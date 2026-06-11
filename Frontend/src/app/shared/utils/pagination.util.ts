export function getTotalPages(total: number, pageSize: number): number {
  if (total <= 0) {
    return 1;
  }
  return Math.ceil(total / pageSize);
}

export function paginateSlice<T>(items: T[], page: number, pageSize: number): T[] {
  const start = (page - 1) * pageSize;
  return items.slice(start, start + pageSize);
}

export function getVisiblePageNumbers(currentPage: number, totalPages: number, maxVisible = 5): number[] {
  if (totalPages <= 1) {
    return [1];
  }

  if (totalPages <= maxVisible) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const half = Math.floor(maxVisible / 2);
  let start = Math.max(1, currentPage - half);
  let end = start + maxVisible - 1;

  if (end > totalPages) {
    end = totalPages;
    start = end - maxVisible + 1;
  }

  return Array.from({ length: end - start + 1 }, (_, index) => start + index);
}

export function getDisplayRange(currentPage: number, pageSize: number, total: number): string {
  if (total <= 0) {
    return '0';
  }

  const start = (currentPage - 1) * pageSize + 1;
  const end = Math.min(currentPage * pageSize, total);
  return `${start} - ${end}`;
}
