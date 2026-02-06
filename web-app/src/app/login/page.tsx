"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { loginSchema, validateForm } from "@/lib/validations";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert } from "@/components/Alert";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const router = useRouter();
  const { login } = useAuth();

  useEffect(() => {
    setMounted(true);
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrors({});
    setServerError(null);

    const validation = validateForm(loginSchema, { email, password });
    if (!validation.success) {
      setErrors(validation.errors);
      return;
    }

    setLoading(true);
    try {
      const { access_token, user } = await api.auth.login(email, password);
      login(access_token, user);
      if (user.plan === "personal") {
        router.push("/app/personal");
      } else {
        router.push("/app");
      }
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 401) {
          setServerError("Invalid email or password.");
        } else if (error.status >= 500) {
          setServerError("Server error. Please try again later.");
        } else {
          setServerError(error.message);
        }
      } else {
        setServerError("Unable to connect. Please check your internet connection.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex">
      {/* Left Panel - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-slate-900 p-12 flex-col justify-between relative overflow-hidden">
        {/* Background decoration */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-slate-700/50 rounded-full blur-3xl" />

        <div className="relative z-10">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-12 h-12 rounded-xl bg-white flex items-center justify-center group-hover:scale-105 transition-transform">
              <span className="text-slate-900 font-bold text-xl">H</span>
            </div>
            <div>
              <span className="font-semibold text-white text-xl">Hisabi</span>
              <span className="block text-sm text-slate-400">SMB Accounting</span>
            </div>
          </Link>
        </div>

        <div className="relative z-10 space-y-6">
          <h2 className="text-4xl font-bold text-white leading-tight">
            Accounting that speaks
            <span className="block text-emerald-400">your language.</span>
          </h2>
          <p className="text-lg text-slate-300 max-w-md">
            Upload your documents, we&apos;ll clean and analyze them. Get balance sheets, P&L, and inventory reports in seconds.
          </p>
          <div className="flex items-center gap-4 pt-4">
            <div className="flex -space-x-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="w-10 h-10 rounded-full bg-gradient-to-br from-slate-600 to-slate-700 border-2 border-slate-900" />
              ))}
            </div>
            <p className="text-sm text-slate-400">
              Trusted by <span className="text-white font-medium">100+ SMBs</span> in Lebanon
            </p>
          </div>
        </div>

        <div className="relative z-10 text-sm text-slate-500">
          © {new Date().getFullYear()} Hisabi. All rights reserved.
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-gradient-to-br from-slate-50 to-white">
        <div className={`w-full max-w-md ${mounted ? 'animate-fade-in-up' : 'opacity-0'}`}>
          {/* Mobile Logo */}
          <div className="lg:hidden mb-8 text-center">
            <Link href="/" className="inline-flex items-center gap-3 group">
              <div className="w-12 h-12 rounded-xl bg-slate-900 flex items-center justify-center group-hover:scale-105 transition-transform">
                <span className="text-white font-bold text-xl">H</span>
              </div>
              <div className="text-left">
                <span className="font-semibold text-slate-900 text-xl">Hisabi</span>
                <span className="block text-sm text-slate-500">SMB Accounting</span>
              </div>
            </Link>
          </div>

          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-slate-900">Welcome back</h1>
            <p className="text-slate-600 mt-2">Sign in to your account to continue</p>
          </div>

          <div className="bg-white rounded-2xl shadow-xl border border-slate-200 p-8">
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="email">Email address</Label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  disabled={loading}
                  autoComplete="email"
                  aria-invalid={!!errors.email}
                  className={`h-12 ${errors.email ? "border-red-500" : ""}`}
                />
                {errors.email && (
                  <p className="text-sm text-red-600 animate-fade-in">{errors.email}</p>
                )}
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <a href="#" className="text-sm text-slate-500 hover:text-slate-700 transition-colors">
                    Forgot password?
                  </a>
                </div>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  disabled={loading}
                  autoComplete="current-password"
                  aria-invalid={!!errors.password}
                  className={`h-12 ${errors.password ? "border-red-500" : ""}`}
                />
                {errors.password && (
                  <p className="text-sm text-red-600 animate-fade-in">{errors.password}</p>
                )}
              </div>

              {serverError && (
                <Alert variant="destructive" className="animate-fade-in">{serverError}</Alert>
              )}

              <Button
                type="submit"
                disabled={loading}
                className="w-full h-12 text-base"
                size="lg"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Signing in...
                  </span>
                ) : (
                  "Sign in"
                )}
              </Button>
            </form>

            <div className="mt-6 text-center text-sm text-slate-500">
              Don&apos;t have an account?{" "}
              <Link href="/login" className="text-slate-900 font-medium hover:underline">
                Contact us
              </Link>
            </div>
          </div>

          <p className="text-center text-xs text-slate-400 mt-6">
            By signing in, you agree to our Terms of Service and Privacy Policy.
          </p>
        </div>
      </div>
    </main>
  );
}
