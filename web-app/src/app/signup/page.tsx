"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { signupSchema, validateForm } from "@/lib/validations";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert } from "@/components/Alert";

export default function SignupPage() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [orgName, setOrgName] = useState("");
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

        const validation = validateForm(signupSchema, { email, password, confirmPassword, org_name: orgName });
        if (!validation.success) {
            setErrors(validation.errors);
            return;
        }

        setLoading(true);
        try {
            const { access_token, user } = await api.auth.register(email, password, orgName);
            login(access_token, user);
            router.push("/personal");
        } catch (error) {
            if (error instanceof ApiError) {
                if (error.status === 400) {
                    const detail = (error.details as { detail?: string })?.detail;
                    setServerError(detail || "Registration failed. Please try again.");
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
                <div className="absolute top-0 right-0 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
                <div className="absolute bottom-0 left-0 w-96 h-96 bg-slate-700/50 rounded-full blur-3xl" />

                <div className="relative z-10">
                    <Link href="/" className="flex items-center gap-3 group">
                        <div className="w-12 h-12 rounded-xl bg-white flex items-center justify-center group-hover:scale-105 transition-transform">
                            <span className="text-slate-900 font-bold text-xl">H</span>
                        </div>
                        <div>
                            <span className="font-semibold text-white text-xl">Hisabi</span>
                            <span className="block text-sm text-slate-400">Personal Finance</span>
                        </div>
                    </Link>
                </div>

                <div className="relative z-10 space-y-6">
                    <h2 className="text-4xl font-bold text-white leading-tight">
                        Take control of
                        <span className="block text-purple-400">your finances.</span>
                    </h2>
                    <p className="text-lg text-slate-300 max-w-md">
                        Track expenses, set budgets, plan ahead, and get AI-powered insights — all in one place.
                    </p>
                    <div className="flex items-center gap-4 pt-4">
                        <div className="flex -space-x-2">
                            {[1, 2, 3].map((i) => (
                                <div key={i} className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 border-2 border-slate-900" />
                            ))}
                        </div>
                        <p className="text-sm text-slate-400">
                            Join <span className="text-white font-medium">thousands</span> managing their money smarter
                        </p>
                    </div>
                </div>

                <div className="relative z-10 text-sm text-slate-500">
                    © {new Date().getFullYear()} Hisabi. All rights reserved.
                </div>
            </div>

            {/* Right Panel - Signup Form */}
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
                                <span className="block text-sm text-slate-500">Personal Finance</span>
                            </div>
                        </Link>
                    </div>

                    <div className="text-center mb-8">
                        <h1 className="text-2xl font-bold text-slate-900">Create your account</h1>
                        <p className="text-slate-600 mt-2">Start tracking your finances in minutes</p>
                    </div>

                    <div className="bg-white rounded-2xl shadow-xl border border-slate-200 p-8">
                        <form onSubmit={handleSubmit} className="space-y-5">
                            <div className="space-y-2">
                                <Label htmlFor="orgName">Your Name</Label>
                                <Input
                                    id="orgName"
                                    type="text"
                                    value={orgName}
                                    onChange={(e) => setOrgName(e.target.value)}
                                    placeholder="John Doe"
                                    disabled={loading}
                                    className={`h-12 ${errors.org_name ? "border-red-500" : ""}`}
                                />
                                {errors.org_name && (
                                    <p className="text-sm text-red-600 animate-fade-in">{errors.org_name}</p>
                                )}
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="email">Email address</Label>
                                <Input
                                    id="email"
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    placeholder="you@example.com"
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
                                <Label htmlFor="password">Password</Label>
                                <Input
                                    id="password"
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                    disabled={loading}
                                    autoComplete="new-password"
                                    aria-invalid={!!errors.password}
                                    className={`h-12 ${errors.password ? "border-red-500" : ""}`}
                                />
                                {errors.password && (
                                    <p className="text-sm text-red-600 animate-fade-in">{errors.password}</p>
                                )}
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="confirmPassword">Confirm Password</Label>
                                <Input
                                    id="confirmPassword"
                                    type="password"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    placeholder="••••••••"
                                    disabled={loading}
                                    autoComplete="new-password"
                                    aria-invalid={!!errors.confirmPassword}
                                    className={`h-12 ${errors.confirmPassword ? "border-red-500" : ""}`}
                                />
                                {errors.confirmPassword && (
                                    <p className="text-sm text-red-600 animate-fade-in">{errors.confirmPassword}</p>
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
                                        Creating account...
                                    </span>
                                ) : (
                                    "Create Account"
                                )}
                            </Button>
                        </form>

                        <div className="mt-6 text-center text-sm text-slate-500">
                            Already have an account?{" "}
                            <Link href="/login" className="text-slate-900 font-medium hover:underline">
                                Sign in
                            </Link>
                        </div>
                    </div>

                    <p className="text-center text-xs text-slate-400 mt-6">
                        By signing up, you agree to our Terms of Service and Privacy Policy.
                    </p>
                </div>
            </div>
        </main>
    );
}
