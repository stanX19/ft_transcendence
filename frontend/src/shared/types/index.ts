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

export interface FileAsset {
  id: number;
  owner_user_id: number | null;
  book_id: number | null;
  kind: string;
  original_filename: string;
  stored_filename: string;
  mime_type: string;
  size_bytes: number;
  created_at: string;
  url: string;
}
