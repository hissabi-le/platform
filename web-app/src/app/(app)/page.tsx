"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function GroupLanding() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/app");
  }, [router]);

  return (
    <main className="p-6 text-sm text-gray-500">
      Redirecting you to the main dashboard…
    </main>
  );
}
