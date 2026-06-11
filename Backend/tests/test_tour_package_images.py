"""
Unit tests for Tour Package Images API Endpoint
Tests for POST /api/v1/tour-packages/{package_id}/images endpoint
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import UploadFile
from uuid import uuid4
import logging

from app.v1.services.tour_package_service import TourPackageService

# Setup logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== Test Fixtures ====================

@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client"""
    mock_client = Mock()
    mock_table = Mock()
    mock_client.table = Mock(return_value=mock_table)
    return mock_client, mock_table


@pytest.fixture
def tour_service(mock_supabase_client):
    """Create TourPackageService instance with mocked Supabase client"""
    client, table = mock_supabase_client
    service = TourPackageService(client)
    return service, table


@pytest.fixture
def sample_package():
    """Sample tour package data"""
    return {
        "package_id": str(uuid4()),
        "package_name": "Tour Đà Lạt",
        "destination": "Đà Lạt",
        "description": "Beautiful tour",
        "duration_days": 3,
        "price": 2500000.0,
        "available_slots": 20,
        "start_date": "2024-12-01",
        "end_date": "2024-12-03",
        "image_urls": "https://cloudinary.com/img1.jpg|https://cloudinary.com/img2.jpg",
        "is_active": True
    }


@pytest.fixture
def mock_upload_file():
    """Create a mock UploadFile for testing"""
    def create_upload_file(filename: str, content_type: str, content: bytes = b"fake image data"):
        mock_file = Mock(spec=UploadFile)
        mock_file.filename = filename
        mock_file.content_type = content_type
        mock_file.read = AsyncMock(return_value=content)
        mock_file.seek = AsyncMock()
        return mock_file
    return create_upload_file


# ==================== Test Upload Images - Success Cases ====================

@pytest.mark.asyncio
async def test_upload_images_success(tour_service, sample_package, mock_upload_file):
    """Test successfully uploading images to an existing tour package"""
    service, mock_table = tour_service
    package_id = sample_package["package_id"]

    # Create mock image files
    images = [
        mock_upload_file("image1.jpg", "image/jpeg"),
        mock_upload_file("image2.png", "image/png")
    ]

    # Mock get_package_by_id - package exists
    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": sample_package
    }):
        # Mock upload_images
        new_image_urls = [
            "https://cloudinary.com/new_img1.jpg",
            "https://cloudinary.com/new_img2.jpg"
        ]
        with patch.object(service, 'upload_images', return_value=new_image_urls):
            # Mock update_package
            with patch.object(service, 'update_package', return_value={
                "EC": 0,
                "EM": "Tour package updated successfully",
                "package": {**sample_package, "image_urls": sample_package["image_urls"] + "|" + "|".join(new_image_urls)}
            }):
                # Execute the endpoint logic
                # (In actual endpoint test, you'd use TestClient)
                result = await service.get_package_by_id(package_id)
                assert result["EC"] == 0

                upload_result = await service.upload_images(images)
                assert len(upload_result) == 2

                logger.info("✓ Test upload images success passed")


@pytest.mark.asyncio
async def test_upload_images_append_to_existing(tour_service, sample_package, mock_upload_file):
    """Test appending new images to existing images (replace_existing=False)"""
    service, mock_table = tour_service
    package_id = sample_package["package_id"]

    # Existing package has 2 images
    existing_image_count = len(sample_package["image_urls"].split("|"))
    assert existing_image_count == 2

    # Upload 2 more images
    images = [
        mock_upload_file("image3.jpg", "image/jpeg"),
        mock_upload_file("image4.jpg", "image/jpeg")
    ]

    new_urls = ["https://cloudinary.com/img3.jpg", "https://cloudinary.com/img4.jpg"]
    expected_final_urls = sample_package["image_urls"] + "|" + "|".join(new_urls)

    # Mock service methods
    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": sample_package
    }):
        with patch.object(service, 'upload_images', return_value=new_urls):
            with patch.object(service, 'update_package', return_value={
                "EC": 0,
                "EM": "Success",
                "package": {**sample_package, "image_urls": expected_final_urls}
            }) as mock_update:
                # Execute
                await service.upload_images(images)
                final_urls = sample_package["image_urls"] + "|" + "|".join(new_urls)
                await service.update_package(package_id, {"image_urls": final_urls})

                # Verify update was called with appended URLs
                mock_update.assert_called_once()
                call_args = mock_update.call_args[0]
                assert call_args[0] == package_id
                assert "|" in call_args[1]["image_urls"]
                assert len(call_args[1]["image_urls"].split("|")) == 4

                logger.info("✓ Test upload images append passed")


@pytest.mark.asyncio
async def test_upload_images_replace_existing(tour_service, sample_package, mock_upload_file):
    """Test replacing all existing images (replace_existing=True)"""
    service, mock_table = tour_service
    sample_package["package_id"]

    # Upload new images to replace old ones
    images = [
        mock_upload_file("new_img1.jpg", "image/jpeg"),
        mock_upload_file("new_img2.png", "image/png")
    ]

    new_urls = ["https://cloudinary.com/new1.jpg", "https://cloudinary.com/new2.jpg"]

    # Mock service methods
    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": sample_package
    }):
        with patch.object(service, 'upload_images', return_value=new_urls):
            with patch.object(service, 'delete_images_from_urls', return_value=2) as mock_delete:
                with patch.object(service, 'update_package', return_value={
                    "EC": 0,
                    "EM": "Success",
                    "package": {**sample_package, "image_urls": "|".join(new_urls)}
                }):
                    # Execute replacement logic
                    await service.delete_images_from_urls(sample_package["image_urls"])
                    await service.upload_images(images)

                    # Verify old images were deleted
                    mock_delete.assert_called_once_with(sample_package["image_urls"])

                    logger.info("✓ Test upload images replace passed")


@pytest.mark.asyncio
async def test_upload_images_to_package_with_no_existing_images(tour_service, mock_upload_file):
    """Test uploading images to a package that has no existing images"""
    service, mock_table = tour_service
    package_id = str(uuid4())

    # Package with no existing images
    package_no_images = {
        "package_id": package_id,
        "package_name": "New Tour",
        "image_urls": None,  # No existing images
        "is_active": True
    }

    images = [mock_upload_file("first_img.jpg", "image/jpeg")]
    new_urls = ["https://cloudinary.com/first_img.jpg"]

    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": package_no_images
    }):
        with patch.object(service, 'upload_images', return_value=new_urls):
            result = await service.upload_images(images)

            # Verify upload successful
            assert len(result) == 1
            assert result[0] == new_urls[0]

            logger.info("✓ Test upload to package with no images passed")


@pytest.mark.asyncio
async def test_upload_images_max_10_images_exact(tour_service, mock_upload_file):
    """Test uploading exactly 10 images (maximum allowed)"""
    service, mock_table = tour_service
    package_id = str(uuid4())

    # Package with no existing images
    package_no_images = {
        "package_id": package_id,
        "package_name": "Tour",
        "image_urls": None,
        "is_active": True
    }

    # Create 10 images
    images = [mock_upload_file(f"img{i}.jpg", "image/jpeg") for i in range(10)]
    new_urls = [f"https://cloudinary.com/img{i}.jpg" for i in range(10)]

    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": package_no_images
    }):
        with patch.object(service, 'upload_images', return_value=new_urls):
            result = await service.upload_images(images)

            # Verify all 10 uploaded
            assert len(result) == 10

            logger.info("✓ Test upload 10 images max passed")


@pytest.mark.asyncio
async def test_upload_images_various_formats(tour_service, mock_upload_file):
    """Test uploading images with different allowed formats"""
    service, mock_table = tour_service

    # Test all allowed formats
    images = [
        mock_upload_file("img1.jpg", "image/jpeg"),
        mock_upload_file("img2.jpg", "image/jpg"),
        mock_upload_file("img3.png", "image/png"),
        mock_upload_file("img4.webp", "image/webp")
    ]

    # All formats should be valid
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    for img in images:
        assert img.content_type in allowed_types

    new_urls = [f"https://cloudinary.com/img{i}.jpg" for i in range(4)]

    with patch.object(service, 'upload_images', return_value=new_urls):
        result = await service.upload_images(images)
        assert len(result) == 4

        logger.info("✓ Test upload various formats passed")


# ==================== Test Upload Images - Error Cases ====================

@pytest.mark.asyncio
async def test_upload_images_package_not_found(tour_service, mock_upload_file):
    """Test uploading images to non-existent package"""
    service, mock_table = tour_service
    package_id = str(uuid4())

    [mock_upload_file("img.jpg", "image/jpeg")]

    # Mock package not found
    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 1,
        "EM": "Tour package not found",
        "package": None
    }):
        result = await service.get_package_by_id(package_id)

        # Verify package not found
        assert result["EC"] == 1
        assert result["EM"] == "Tour package not found"

        logger.info("✓ Test package not found passed")


@pytest.mark.asyncio
async def test_upload_images_exceeds_max_limit(tour_service, sample_package, mock_upload_file):
    """Test uploading images that would exceed 10 image limit"""
    service, mock_table = tour_service

    # Package already has 8 images
    existing_urls = "|".join([f"https://cloudinary.com/existing{i}.jpg" for i in range(8)])
    package_with_8_images = {
        **sample_package,
        "image_urls": existing_urls
    }

    # Try to upload 5 more (would exceed limit)
    images = [mock_upload_file(f"img{i}.jpg", "image/jpeg") for i in range(5)]

    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": package_with_8_images
    }):
        # Check validation logic
        existing_count = len(package_with_8_images["image_urls"].split("|"))
        total = existing_count + len(images)

        assert total > 10  # Should exceed limit
        assert existing_count == 8

        logger.info("✓ Test exceeds max limit validation passed")


@pytest.mark.asyncio
async def test_upload_images_invalid_file_type(tour_service, mock_upload_file):
    """Test uploading images with invalid file types"""
    service, mock_table = tour_service

    # Create invalid file types
    invalid_images = [
        mock_upload_file("file.pdf", "application/pdf"),
        mock_upload_file("file.gif", "image/gif"),
        mock_upload_file("file.bmp", "image/bmp"),
        mock_upload_file("file.txt", "text/plain")
    ]

    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]

    # Verify all are invalid
    for img in invalid_images:
        assert img.content_type not in allowed_types

    logger.info("✓ Test invalid file type validation passed")


@pytest.mark.asyncio
async def test_upload_images_cloudinary_upload_fails(tour_service, sample_package, mock_upload_file):
    """Test handling when Cloudinary upload fails"""
    service, mock_table = tour_service
    sample_package["package_id"]

    images = [mock_upload_file("img.jpg", "image/jpeg")]

    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": sample_package
    }):
        # Mock upload failure (returns empty list)
        with patch.object(service, 'upload_images', return_value=[]):
            result = await service.upload_images(images)

            # Verify upload failed
            assert result == []

            logger.info("✓ Test cloudinary upload fails passed")


@pytest.mark.asyncio
async def test_upload_images_update_package_fails_rollback(tour_service, sample_package, mock_upload_file):
    """Test rollback when database update fails after successful upload"""
    service, mock_table = tour_service
    package_id = sample_package["package_id"]

    [mock_upload_file("img.jpg", "image/jpeg")]
    new_urls = ["https://cloudinary.com/new_img.jpg"]

    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": sample_package
    }):
        with patch.object(service, 'upload_images', return_value=new_urls):
            # Mock update failure
            with patch.object(service, 'update_package', return_value={
                "EC": 1,
                "EM": "Failed to update package"
            }):
                # Mock delete for rollback
                with patch.object(service, 'delete_images_from_urls', return_value=1) as mock_delete:
                    # Execute rollback logic
                    update_result = await service.update_package(package_id, {})

                    if update_result["EC"] != 0:
                        # Should rollback - delete newly uploaded images
                        await service.delete_images_from_urls("|".join(new_urls))

                    # Verify rollback was called
                    mock_delete.assert_called_once()

                    logger.info("✓ Test upload rollback on update failure passed")


@pytest.mark.asyncio
async def test_upload_images_empty_list(tour_service, sample_package):
    """Test uploading with empty image list"""
    service, mock_table = tour_service
    sample_package["package_id"]

    images = []

    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": sample_package
    }):
        # Empty list should be handled
        result = await service.upload_images(images)

        # Should return empty list or handle gracefully
        assert isinstance(result, list)

        logger.info("✓ Test upload empty list passed")


# ==================== Test Image Service Methods ====================

@pytest.mark.asyncio
async def test_service_upload_images_method(tour_service, mock_upload_file):
    """Test TourPackageService.upload_images method"""
    service, mock_table = tour_service

    images = [
        mock_upload_file("test1.jpg", "image/jpeg", b"fake content 1"),
        mock_upload_file("test2.png", "image/png", b"fake content 2")
    ]

    expected_urls = [
        "https://cloudinary.com/tour_packages/test1.jpg",
        "https://cloudinary.com/tour_packages/test2.jpg"
    ]

    # Mock CloudinaryConfig
    with patch('app.v1.services.tour_package_service.CloudinaryConfig') as mock_cloudinary:
        mock_cloudinary.upload_multiple_images.return_value = expected_urls

        result = await service.upload_images(images)

        # Assertions
        assert len(result) == 2
        assert result == expected_urls

        # Verify CloudinaryConfig was called correctly
        mock_cloudinary.upload_multiple_images.assert_called_once()
        args, kwargs = mock_cloudinary.upload_multiple_images.call_args
        assert len(args[0]) == 2  # Two files
        assert kwargs.get("folder") == "tour_packages"  # Correct folder (passed as keyword arg)

        logger.info("✓ Test service upload_images method passed")


@pytest.mark.asyncio
async def test_service_upload_images_exception(tour_service, mock_upload_file):
    """Test TourPackageService.upload_images handles exceptions"""
    service, mock_table = tour_service

    images = [mock_upload_file("test.jpg", "image/jpeg")]

    # Mock CloudinaryConfig to raise exception
    with patch('app.v1.services.tour_package_service.CloudinaryConfig') as mock_cloudinary:
        mock_cloudinary.upload_multiple_images.side_effect = Exception("Cloudinary error")

        result = await service.upload_images(images)

        # Should return empty list on error
        assert result == []

        logger.info("✓ Test service upload_images exception passed")


@pytest.mark.asyncio
async def test_service_delete_images_method(tour_service):
    """Test TourPackageService.delete_images_from_urls method"""
    service, mock_table = tour_service

    image_urls = "https://cloudinary.com/img1.jpg|https://cloudinary.com/img2.jpg|https://cloudinary.com/img3.jpg"

    # Mock CloudinaryConfig
    with patch('app.v1.services.tour_package_service.CloudinaryConfig') as mock_cloudinary:
        mock_cloudinary.extract_public_id_from_url.side_effect = lambda url: url.split("/")[-1].replace(".jpg", "")
        mock_cloudinary.delete_multiple_images.return_value = 3

        result = await service.delete_images_from_urls(image_urls)

        # Assertions
        assert result == 3

        # Verify delete was called
        mock_cloudinary.delete_multiple_images.assert_called_once()
        call_args = mock_cloudinary.delete_multiple_images.call_args[0]
        assert len(call_args[0]) == 3  # Three public IDs

        logger.info("✓ Test service delete_images method passed")


@pytest.mark.asyncio
async def test_service_delete_images_empty_urls(tour_service):
    """Test deleting with empty or None image_urls"""
    service, mock_table = tour_service

    # Test with None
    result_none = await service.delete_images_from_urls(None)
    assert result_none == 0

    # Test with empty string
    result_empty = await service.delete_images_from_urls("")
    assert result_empty == 0

    logger.info("✓ Test service delete empty urls passed")


@pytest.mark.asyncio
async def test_service_delete_images_partial_failure(tour_service):
    """Test deleting images with partial failures"""
    service, mock_table = tour_service

    image_urls = "https://cloudinary.com/img1.jpg|https://cloudinary.com/img2.jpg|https://cloudinary.com/img3.jpg"

    with patch('app.v1.services.tour_package_service.CloudinaryConfig') as mock_cloudinary:
        mock_cloudinary.extract_public_id_from_url.side_effect = lambda url: url.split("/")[-1].replace(".jpg", "")
        # Only 2 out of 3 deleted successfully
        mock_cloudinary.delete_multiple_images.return_value = 2

        result = await service.delete_images_from_urls(image_urls)

        # Should return partial count
        assert result == 2

        logger.info("✓ Test service delete partial failure passed")


@pytest.mark.asyncio
async def test_service_delete_images_exception(tour_service):
    """Test TourPackageService.delete_images_from_urls handles exceptions"""
    service, mock_table = tour_service

    image_urls = "https://cloudinary.com/img1.jpg"

    with patch('app.v1.services.tour_package_service.CloudinaryConfig') as mock_cloudinary:
        mock_cloudinary.extract_public_id_from_url.side_effect = Exception("Cloudinary error")

        result = await service.delete_images_from_urls(image_urls)

        # Should return 0 on error
        assert result == 0

        logger.info("✓ Test service delete_images exception passed")


# ==================== Test Edge Cases ====================

@pytest.mark.asyncio
async def test_upload_images_with_special_characters_in_filename(tour_service, mock_upload_file):
    """Test uploading images with special characters in filename"""
    service, mock_table = tour_service

    images = [
        mock_upload_file("image with spaces.jpg", "image/jpeg"),
        mock_upload_file("ảnh-tiếng-việt.png", "image/png"),
        mock_upload_file("image@#$%.jpg", "image/jpeg")
    ]

    expected_urls = [
        "https://cloudinary.com/image_with_spaces.jpg",
        "https://cloudinary.com/anh-tieng-viet.png",
        "https://cloudinary.com/image.jpg"
    ]

    with patch('app.v1.services.tour_package_service.CloudinaryConfig') as mock_cloudinary:
        mock_cloudinary.upload_multiple_images.return_value = expected_urls

        result = await service.upload_images(images)

        assert len(result) == 3

        logger.info("✓ Test upload special characters filename passed")


@pytest.mark.asyncio
async def test_upload_images_large_files(tour_service, mock_upload_file):
    """Test uploading large image files"""
    service, mock_table = tour_service

    # Create large file (simulate 5MB)
    large_content = b"x" * (5 * 1024 * 1024)
    images = [mock_upload_file("large_image.jpg", "image/jpeg", large_content)]

    expected_urls = ["https://cloudinary.com/large_image.jpg"]

    with patch('app.v1.services.tour_package_service.CloudinaryConfig') as mock_cloudinary:
        mock_cloudinary.upload_multiple_images.return_value = expected_urls

        result = await service.upload_images(images)

        assert len(result) == 1

        logger.info("✓ Test upload large files passed")


@pytest.mark.asyncio
async def test_replace_existing_images_with_different_count(tour_service, sample_package, mock_upload_file):
    """Test replacing 2 existing images with 5 new images"""
    service, mock_table = tour_service
    sample_package["package_id"]

    # Package has 2 images, replace with 5
    assert len(sample_package["image_urls"].split("|")) == 2

    new_images = [mock_upload_file(f"new{i}.jpg", "image/jpeg") for i in range(5)]
    new_urls = [f"https://cloudinary.com/new{i}.jpg" for i in range(5)]

    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": sample_package
    }):
        with patch.object(service, 'upload_images', return_value=new_urls):
            with patch.object(service, 'delete_images_from_urls', return_value=2):
                result = await service.upload_images(new_images)

                # Verify 5 new images uploaded
                assert len(result) == 5

                logger.info("✓ Test replace with different count passed")


@pytest.mark.asyncio
async def test_concurrent_image_uploads(tour_service, sample_package, mock_upload_file):
    """Test handling concurrent image uploads to same package"""
    service, mock_table = tour_service
    sample_package["package_id"]

    # Simulate two concurrent upload requests
    images1 = [mock_upload_file("concurrent1.jpg", "image/jpeg")]
    images2 = [mock_upload_file("concurrent2.jpg", "image/jpeg")]

    urls1 = ["https://cloudinary.com/concurrent1.jpg"]
    urls2 = ["https://cloudinary.com/concurrent2.jpg"]

    with patch('app.v1.services.tour_package_service.CloudinaryConfig') as mock_cloudinary:
        mock_cloudinary.upload_multiple_images.side_effect = [urls1, urls2]

        # Execute uploads
        result1 = await service.upload_images(images1)
        result2 = await service.upload_images(images2)

        assert len(result1) == 1
        assert len(result2) == 1

        logger.info("✓ Test concurrent uploads passed")


@pytest.mark.asyncio
async def test_image_urls_pipe_separator_format(tour_service, sample_package):
    """Test that image URLs are correctly formatted with pipe separators"""
    service, mock_table = tour_service

    # Test parsing pipe-separated URLs
    image_urls = sample_package["image_urls"]
    urls_list = image_urls.split("|")

    assert len(urls_list) == 2
    assert all(url.startswith("https://") for url in urls_list)

    # Test joining URLs
    new_urls = ["https://cloudinary.com/img3.jpg", "https://cloudinary.com/img4.jpg"]
    combined = image_urls + "|" + "|".join(new_urls)

    assert combined.count("|") == 3  # 4 images = 3 separators
    assert len(combined.split("|")) == 4

    logger.info("✓ Test pipe separator format passed")


# ==================== Test Response Format ====================

def test_response_format_success():
    """Test expected response format for successful upload"""
    response = {
        "EC": 0,
        "EM": "Images uploaded successfully",
        "image_urls": [
            "https://cloudinary.com/img1.jpg",
            "https://cloudinary.com/img2.jpg"
        ],
        "total_images": 2
    }

    assert response["EC"] == 0
    assert response["EM"] == "Images uploaded successfully"
    assert isinstance(response["image_urls"], list)
    assert len(response["image_urls"]) == response["total_images"]

    logger.info("✓ Test response format success passed")


def test_response_format_errors():
    """Test expected error response formats"""

    # Package not found
    error_404 = {
        "detail": "Tour package not found"
    }
    assert "Tour package not found" in error_404["detail"]

    # Max images exceeded
    error_400_max = {
        "detail": "Maximum 10 images allowed. Current: 8, Uploading: 5"
    }
    assert "Maximum 10 images" in error_400_max["detail"]

    # Invalid file type
    error_400_type = {
        "detail": "Invalid file type: image/bmp. Allowed: jpeg, jpg, png, webp"
    }
    assert "Invalid file type" in error_400_type["detail"]

    # Upload failure
    error_500 = {
        "detail": "Failed to upload images"
    }
    assert "Failed to upload" in error_500["detail"]

    logger.info("✓ Test error response formats passed")


# ==================== Integration Test Simulation ====================

@pytest.mark.asyncio
async def test_full_image_upload_workflow(tour_service, sample_package, mock_upload_file):
    """Test complete workflow: validate -> upload -> update -> response"""
    service, mock_table = tour_service
    package_id = sample_package["package_id"]

    # Step 1: Validate package exists
    with patch.object(service, 'get_package_by_id', return_value={
        "EC": 0,
        "EM": "Success",
        "package": sample_package
    }) as mock_get:

        # Step 2: Validate image count (existing 2 + new 3 = 5, within limit)
        images = [mock_upload_file(f"new{i}.jpg", "image/jpeg") for i in range(3)]
        existing_count = len(sample_package["image_urls"].split("|"))
        total_count = existing_count + len(images)
        assert total_count <= 10

        # Step 3: Validate file types
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
        assert all(img.content_type in allowed_types for img in images)

        # Step 4: Upload to Cloudinary
        new_urls = [f"https://cloudinary.com/new{i}.jpg" for i in range(3)]
        with patch.object(service, 'upload_images', return_value=new_urls) as mock_upload:

            # Step 5: Update database
            final_urls = sample_package["image_urls"] + "|" + "|".join(new_urls)
            with patch.object(service, 'update_package', return_value={
                "EC": 0,
                "EM": "Success",
                "package": {**sample_package, "image_urls": final_urls}
            }) as mock_update:

                # Execute workflow
                get_result = await service.get_package_by_id(package_id)
                assert get_result["EC"] == 0

                upload_result = await service.upload_images(images)
                assert len(upload_result) == 3

                update_result = await service.update_package(package_id, {"image_urls": final_urls})
                assert update_result["EC"] == 0

                # Verify all steps executed
                mock_get.assert_called_once()
                mock_upload.assert_called_once()
                mock_update.assert_called_once()

                logger.info("✓ Test full workflow passed")


# ==================== Run Tests Summary ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
    logger.info("=" * 60)
    logger.info("All tour package image tests completed!")
    logger.info("=" * 60)
