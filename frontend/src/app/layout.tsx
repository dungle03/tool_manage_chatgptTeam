import "./globals.css";

export const metadata = {
  title: "Workspace Manager",
  description: "Manage your ChatGPT Team workspaces in one unified dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
