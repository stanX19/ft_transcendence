/** Shared transport and UI types belong here. */

export type UserRole = "MEMBER" | "LIBRARIAN" | "ADMIN";

export interface AuthUser {
  id: number;
  email: string;
  display_name: string;
  bio: string;
  role: UserRole | string;
  is_online: boolean;
}

export interface PublicUser {
  id: number;
  display_name: string;
  bio: string;
  is_online: boolean;
}

export interface UserDirectoryResponse {
  items: PublicUser[];
  page: number;
  page_size: number;
  total: number;
}
