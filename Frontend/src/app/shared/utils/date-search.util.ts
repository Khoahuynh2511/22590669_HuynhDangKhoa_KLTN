export function getMinSearchDate(): string {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function validateSearchDepartureDate(date: string): string | null {
  if (!date?.trim()) {
    return 'Vui lòng chọn ngày đi';
  }

  if (date < getMinSearchDate()) {
    return 'Ngày đi không được ở quá khứ';
  }

  return null;
}

export function validateSearchReturnDate(departureDate: string, returnDate: string): string | null {
  if (!returnDate?.trim()) {
    return 'Vui lòng chọn ngày về';
  }

  if (returnDate < departureDate) {
    return 'Ngày về phải sau hoặc bằng ngày đi';
  }

  return null;
}
