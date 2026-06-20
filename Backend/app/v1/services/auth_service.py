"""
Authentication Service
Handles user registration, login, and token verification
"""
import logging
import bcrypt
import jwt
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from supabase import Client
from ..core.config import settings

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for user management"""

    def __init__(self, supabase_client: Client = None):
        """
        Initialize AuthService

        Args:
            supabase_client: Supabase client instance (deprecated, ignored for backward compatibility)
        """
        # supabase_client parameter kept for backward compatibility but no longer used
        self.jwt_secret = settings.JWT_SECRET
        self.jwt_expire = settings.JWT_EXPIRE
        self.salt_rounds = 10

    def _pg_conn(self):
        return psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)

    @staticmethod
    def _normalize_user(user: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(user)
        normalized["user_id"] = str(normalized.get("user_id"))
        normalized["phone_number"] = normalized.get("phone")
        normalized["is_activate"] = normalized.get("is_active", True)
        # email_verified: default True (user cũ / không có cột → coi như đã verify)
        normalized["email_verified"] = normalized.get("email_verified", True)
        return normalized

    def _hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt

        Args:
            password: Plain text password

        Returns:
            str: Hashed password
        """
        salt = bcrypt.gensalt(rounds=self.salt_rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verify password against hashed password

        Args:
            password: Plain text password
            hashed_password: Hashed password from database

        Returns:
            bool: True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False

    def _generate_access_token(self, user_data: Dict[str, Any]) -> str:
        """
        Generate JWT access token

        Args:
            user_data: User data to include in token payload (must include email, full_name, user_id, role)

        Returns:
            str: JWT access token
        """
        payload = {
            "email": user_data["email"],
            "full_name": user_data["full_name"],
            "user_id": user_data["user_id"],
            "role": user_data.get("role", "user"),  # Include role in JWT
            "exp": datetime.now(timezone.utc) + timedelta(days=self.jwt_expire)
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        return token

    async def register_user(
        self,
        full_name: str,
        email: str,
        password: str,
        phone_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new user. Sau khi tạo tài khoản (email_verified=False),
        sinh OTP và gửi email xác thực. User phải verify OTP mới login được.

        Args:
            full_name: User's full name
            email: User's email address
            password: User's password
            phone_number: Optional phone number

        Returns:
            Dict containing registration result (awaiting_verification=True)
        """
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
                    if cur.fetchone():
                        return {
                            "EC": 1,
                            "EM": "Email already exists"
                        }

                    hashed_password = self._hash_password(password)
                    # email_verified=False: user phải verify OTP qua email mới login được
                    cur.execute(
                        """
                        INSERT INTO users (full_name, email, password_hash, phone, is_active, email_verified, role)
                        VALUES (%s, %s, %s, %s, true, false, 'user')
                        RETURNING user_id, email, full_name, phone, email_verified
                        """,
                        (full_name, email, hashed_password, phone_number),
                    )
                    user = self._normalize_user(cur.fetchone())
                    conn.commit()

            # Sinh OTP và gửi email xác thực (non-fatal: user vẫn tạo được dù email fail)
            otp_sent = self._send_email_verification_otp(email)

            return {
                "EC": 0,
                "EM": "User registered successfully. Vui lòng kiểm tra email để xác thực tài khoản.",
                "user": {
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "full_name": user["full_name"],
                    "phone_number": user.get("phone_number")
                },
                "awaiting_verification": True,
                "otp_sent": otp_sent
            }

        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
            return {
                "EC": 3,
                "EM": f"Registration error: {str(e)}"
            }

    def _send_email_verification_otp(self, email: str) -> bool:
        """
        Sinh OTP, lưu vào Redis (key otp:{email}) và gửi email xác thực.

        Returns:
            True nếu gửi email thành công, False nếu fail (non-fatal).
        """
        try:
            from .otp_service import get_otp_service
            otp_service = get_otp_service()
            otp = otp_service.generate_otp()

            # Lưu OTP vào Redis (tái dụng store_otp)
            stored = otp_service.store_otp(email, otp)
            if not stored:
                logger.warning(
                    f"Redis not available - cannot persist OTP for {email}. OTP: {otp}")

            # Gửi email (tour_name=None -> template generic "Mã xác thực của bạn")
            sent = otp_service.send_otp_email(email=email, otp=otp, tour_name=None)
            if not sent:
                logger.warning(f"Failed to send verification email to {email}. OTP: {otp}")
            return sent
        except Exception as e:
            logger.error(f"Error sending email verification OTP to {email}: {str(e)}")
            return False

    async def verify_email(self, email: str, otp: str) -> Dict[str, Any]:
        """
        Verify email bằng OTP code. Nếu hợp lệ -> set email_verified=True.

        Args:
            email: User email address
            otp: 6-digit OTP code

        Returns:
            Dict with EC, EM
        """
        try:
            from .otp_service import get_otp_service
            otp_service = get_otp_service()

            is_valid = otp_service.verify_otp(email, otp)
            if not is_valid:
                return {
                    "EC": 1,
                    "EM": "Mã xác thực không đúng hoặc đã hết hạn"
                }

            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET email_verified = TRUE WHERE email = %s",
                        (email,)
                    )
                    conn.commit()

            return {
                "EC": 0,
                "EM": "Xác thực email thành công. Bạn có thể đăng nhập."
            }

        except Exception as e:
            logger.error(f"Error verifying email for {email}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Verification error: {str(e)}"
            }

    async def resend_verification_email(self, email: str) -> Dict[str, Any]:
        """
        Gửi lại OTP xác thực email (khi user chưa nhận được hoặc OTP hết hạn).

        Args:
            email: User email address

        Returns:
            Dict with EC, EM
        """
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT email_verified FROM users WHERE email = %s",
                        (email,)
                    )
                    row = cur.fetchone()

            if not row:
                return {
                    "EC": 1,
                    "EM": "Không tìm thấy tài khoản với email này"
                }

            if dict(row).get('email_verified', True):
                return {
                    "EC": 2,
                    "EM": "Email đã được xác thực"
                }

            otp_sent = self._send_email_verification_otp(email)
            return {
                "EC": 0,
                "EM": "Đã gửi lại mã xác thực. Vui lòng kiểm tra email.",
                "otp_sent": otp_sent
            }

        except Exception as e:
            logger.error(f"Error resending verification to {email}: {str(e)}")
            return {
                "EC": 3,
                "EM": f"Error: {str(e)}"
            }

    async def forgot_password(self, email: str) -> Dict[str, Any]:
        """
        Khởi tạo đặt lại mật khẩu: sinh OTP, lưu Redis (key reset_password:{email}),
        gửi email. Luôn trả EC=0 để tránh leak email tồn tại hay không.

        Args:
            email: User email address

        Returns:
            Dict with EC, EM
        """
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
                    row = cur.fetchone()

            if not row:
                # Tránh leak: vẫn báo "đã gửi" dù email không tồn tại
                return {
                    "EC": 0,
                    "EM": "Nếu email tồn tại, mã đặt lại mật khẩu đã được gửi."
                }

            from .otp_service import get_otp_service
            otp_service = get_otp_service()
            otp = otp_service.generate_otp()

            key = f"reset_password:{email.lower().strip()}"
            if otp_service.redis_client:
                expire_seconds = settings.OTP_EXPIRE_MINUTES * 60
                otp_service.redis_client.setex(key, expire_seconds, otp)
            else:
                logger.warning(
                    f"Redis not available - cannot persist reset OTP for {email}. OTP: {otp}")

            sent = otp_service.send_otp_email(email=email, otp=otp, tour_name=None)

            return {
                "EC": 0,
                "EM": "Nếu email tồn tại, mã đặt lại mật khẩu đã được gửi.",
                "otp_sent": sent
            }

        except Exception as e:
            logger.error(f"Error in forgot_password for {email}: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error: {str(e)}"
            }

    async def reset_password(
        self,
        email: str,
        otp: str,
        new_password: str
    ) -> Dict[str, Any]:
        """
        Đặt lại mật khẩu: verify OTP từ Redis (key reset_password:{email}),
        nếu OK thì cập nhật password_hash.

        Args:
            email: User email address
            otp: 6-digit OTP code
            new_password: Mật khẩu mới

        Returns:
            Dict with EC, EM
        """
        try:
            from .otp_service import get_otp_service
            otp_service = get_otp_service()

            if not otp_service.redis_client:
                return {
                    "EC": 1,
                    "EM": "Dịch vụ OTP không khả dụng, vui lòng thử lại sau."
                }

            key = f"reset_password:{email.lower().strip()}"
            stored_otp = otp_service.redis_client.get(key)

            if stored_otp is None:
                return {
                    "EC": 2,
                    "EM": "Mã đặt lại không đúng hoặc đã hết hạn"
                }

            if stored_otp != otp:
                return {
                    "EC": 2,
                    "EM": "Mã đặt lại không đúng"
                }

            # OTP đúng -> xóa key, cập nhật password
            otp_service.redis_client.delete(key)
            hashed_password = self._hash_password(new_password)

            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET password_hash = %s WHERE email = %s",
                        (hashed_password, email)
                    )
                    conn.commit()

            return {
                "EC": 0,
                "EM": "Đặt lại mật khẩu thành công. Bạn có thể đăng nhập bằng mật khẩu mới."
            }

        except Exception as e:
            logger.error(f"Error resetting password for {email}: {str(e)}")
            return {
                "EC": 3,
                "EM": f"Error: {str(e)}"
            }

    async def login_user(
        self,
        password: str,
        email: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate user and generate access token
        Can login with either email or phone_number

        Args:
            password: User's password
            email: User's email address (optional)
            phone_number: User's phone number (optional)

        Returns:
            Dict containing login result with access token
        """
        try:
            # Validate that at least one identifier is provided
            if not email and not phone_number:
                return {
                    "EC": 1,
                    "EM": "Either email or phone_number must be provided"
                }

            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    if email:
                        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
                    else:
                        cur.execute("SELECT * FROM users WHERE phone = %s", (phone_number,))
                    row = cur.fetchone()

            if not row:
                return {
                    "EC": 2,
                    "EM": "Email/Phone/Password is incorrect"
                }

            user = self._normalize_user(row)

            if not user.get('password_hash'):
                return {
                    "EC": 2,
                    "EM": "Email/Phone/Password is incorrect"
                }

            if not self._verify_password(password, user['password_hash']):
                return {
                    "EC": 2,
                    "EM": "Email/Phone/Password is incorrect"
                }

            if not user.get('is_activate', True):
                return {
                    "EC": 3,
                    "EM": "Account is not activated"
                }

            # Chặn login nếu email chưa xác thực
            if not user.get('email_verified', True):
                return {
                    "EC": 5,
                    "EM": "Tài khoản chưa xác thực email. Vui lòng kiểm tra email để nhập mã xác thực."
                }

            role = user.get('role', 'user')

            # Generate access token
            access_token = self._generate_access_token({
                "email": user["email"],
                "full_name": user["full_name"],
                "user_id": user["user_id"],
                "role": role
            })

            return {
                "EC": 0,
                "EM": "Login successful",
                "access_token": access_token,
                "user": {
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "full_name": user["full_name"],
                    "phone_number": user.get("phone_number"),
                    "role": role
                }
            }

        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return {
                "EC": 4,
                "EM": f"Login error: {str(e)}"
            }

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT access token

        Args:
            token: JWT access token

        Returns:
            Dict containing verification result
        """
        try:
            decoded = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return {
                "EC": 0,
                "EM": "Token is valid",
                "data": {
                    "email": decoded.get("email"),
                    "full_name": decoded.get("full_name"),
                    "user_id": decoded.get("user_id"),
                    "role": decoded.get("role", "user"),  # Include role from JWT
                    "exp": decoded.get("exp")
                }
            }
        except jwt.ExpiredSignatureError:
            return {
                "EC": 1,
                "EM": "Token has expired"
            }
        except jwt.InvalidTokenError as e:
            return {
                "EC": 2,
                "EM": f"Token is invalid: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error verifying token: {str(e)}")
            return {
                "EC": 3,
                "EM": f"Token verification error: {str(e)}"
            }

    def get_user_role(self, user_id: str) -> Optional[str]:
        """
        Get user role from database

        Args:
            user_id: UUID of the user

        Returns:
            User role ('user' or 'admin') or None if user doesn't exist
        """
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT role FROM users WHERE user_id = %s",
                        (user_id,)
                    )
                    row = cur.fetchone()

            if not row:
                logger.warning(f"User {user_id} not found")
                return None

            role = row.get('role', 'user')
            return role

        except Exception as e:
            logger.error(f"Error getting user role for {user_id}: {str(e)}")
            return None

    def get_user_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user role and active status from database

        Args:
            user_id: UUID of the user

        Returns:
            Dict with role and is_active, or None if user doesn't exist
        """
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT role, is_active FROM users WHERE user_id = %s",
                        (user_id,)
                    )
                    row = cur.fetchone()

            if not row:
                logger.warning(f"User {user_id} not found")
                return None

            return {
                'role': row.get('role', 'user'),
                'is_active': row.get('is_active', True)
            }

        except Exception as e:
            logger.error(f"Error getting user status for {user_id}: {str(e)}")
            return None

    async def register_admin(
        self,
        full_name: str,
        email: str,
        password: str,
        phone_number: Optional[str] = None,
        admin_secret_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register a new admin user

        Args:
            full_name: Admin's full name
            email: Admin's email address
            password: Admin's password
            phone_number: Optional phone number
            admin_secret_key: Secret key để verify quyền tạo admin (optional, có thể check từ config)

        Returns:
            Dict containing registration result
        """
        try:
            # Check if admin secret key is required and valid
            required_secret = getattr(settings, 'ADMIN_SECRET_KEY', None)

            if required_secret and admin_secret_key != required_secret:
                return {
                    "EC": 1,
                    "EM": "Invalid admin secret key"
                }

            # Hash password
            hashed_password = self._hash_password(password)

            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    # Check if user already exists
                    cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
                    if cur.fetchone():
                        return {
                            "EC": 2,
                            "EM": "Email already exists"
                        }

                    # Create admin user in database
                    cur.execute(
                        """
                        INSERT INTO users (full_name, email, password_hash, phone, is_active, role)
                        VALUES (%s, %s, %s, %s, true, 'admin')
                        RETURNING user_id, email, full_name, phone, role
                        """,
                        (full_name, email, hashed_password, phone_number),
                    )
                    user = self._normalize_user(cur.fetchone())
                    conn.commit()

            return {
                "EC": 0,
                "EM": "Admin registered successfully",
                "user": {
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "full_name": user["full_name"],
                    "phone_number": user.get("phone_number"),
                    "role": user.get("role", "admin")
                }
            }

        except Exception as e:
            logger.error(f"Error registering admin: {str(e)}")
            return {
                "EC": 4,
                "EM": f"Admin registration error: {str(e)}"
            }

    async def login_admin(
        self,
        password: str,
        email: Optional[str] = None,
        phone_number: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate admin user and generate access token
        Verify user có role = 'admin' sau khi login thành công

        Args:
            password: Admin's password
            email: Admin's email address (optional)
            phone_number: Admin's phone number (optional)

        Returns:
            Dict containing login result with access token
        """
        try:
            # Validate that at least one identifier is provided
            if not email and not phone_number:
                return {
                    "EC": 1,
                    "EM": "Either email or phone_number must be provided"
                }

            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    # Fetch user by email or phone_number
                    if email:
                        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
                    else:
                        cur.execute("SELECT * FROM users WHERE phone = %s", (phone_number,))
                    row = cur.fetchone()

            if not row:
                return {
                    "EC": 2,
                    "EM": "Email/Phone/Password is incorrect"
                }

            user = self._normalize_user(row)

            # Check if user has password (TRADITIONAL login)
            if not user.get('password_hash'):
                return {
                    "EC": 2,
                    "EM": "Email/Phone/Password is incorrect"
                }

            # Verify password
            if not self._verify_password(password, user['password_hash']):
                return {
                    "EC": 2,
                    "EM": "Email/Phone/Password is incorrect"
                }

            # Check if account is activated
            if not user.get('is_activate', True):
                return {
                    "EC": 3,
                    "EM": "Account is not activated"
                }

            # Chặn login nếu email chưa xác thực
            if not user.get('email_verified', True):
                return {
                    "EC": 6,
                    "EM": "Tài khoản chưa xác thực email. Vui lòng kiểm tra email để nhập mã xác thực."
                }

            # Verify user is admin
            role = user.get('role', 'user')
            if role != 'admin':
                return {
                    "EC": 4,
                    "EM": "Access denied. Admin privileges required."
                }

            # Generate access token
            access_token = self._generate_access_token({
                "email": user["email"],
                "full_name": user["full_name"],
                "user_id": user["user_id"],
                "role": role
            })

            return {
                "EC": 0,
                "EM": "Admin login successful",
                "access_token": access_token,
                "user": {
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "full_name": user["full_name"],
                    "phone_number": user.get("phone_number"),
                    "role": role
                }
            }

        except Exception as e:
            logger.error(f"Error during admin login: {str(e)}")
            return {
                "EC": 5,
                "EM": f"Admin login error: {str(e)}"
            }
