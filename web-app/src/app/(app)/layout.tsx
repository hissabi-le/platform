import Protected from "@/components/Protected";
import AppShell from "@/components/AppShell";

export default function AppGroupLayout({ children }: { children: React.ReactNode }) {
  return (
    <Protected>
      <AppShell>{children}</AppShell>
    </Protected>
  );
}
