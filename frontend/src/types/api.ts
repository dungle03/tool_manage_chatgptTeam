export type Workspace = {
  id: number;
  org_id: string;
  name: string;
  member_limit: number;
  created_at: string;
};

export type Member = {
  id: number;
  name: string;
  email: string;
  role: string;
  status: string;
  invite_date: string | null;
};
