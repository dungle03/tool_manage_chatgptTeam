export type Workspace = {
  id: number;
  org_id: string;
  account_id: string | null;
  name: string;
  status: string;
  member_count: number;
  member_limit: number;
  expires_at: string | null;
  last_sync: string | null;
  created_at: string;
};

export type Member = {
  id: number;
  remote_id: string | null;
  name: string;
  email: string;
  role: string;
  status: string;
  invite_date: string | null;
  created_at: string | null;
  picture: string | null;
};

export type Invite = {
  id: number;
  org_id: string;
  email: string;
  invite_id: string;
  status: string;
  created_at: string;
};
