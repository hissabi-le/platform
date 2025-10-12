"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
  const [email, setEmail] = useState("owner@demo.local");
  const [password, setPassword] = useState("demo123");
  const [err, setErr] = useState<string | null>(null);
  const router = useRouter();
  const { login } = useAuth();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      const { token, user } = await api.auth.login(email, password);
      login(token, user);
      router.push("/app");
    } catch {
      setErr("Login failed");
    }
  }

  return (
    <main className="p-6 max-w-md mx-auto">
      <h1 className="text-xl font-semibold mb-4">Login</h1>
      <form onSubmit={submit} className="space-y-3">
        <input className="w-full border p-2 rounded" value={email} onChange={e=>setEmail(e.target.value)} placeholder="Email" />
        <input className="w-full border p-2 rounded" type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Password" />
        {err && <p className="text-red-600 text-sm">{err}</p>}
        <button className="px-4 py-2 rounded bg-black text-white">Sign in</button>
      </form>
    </main>
  );
}
