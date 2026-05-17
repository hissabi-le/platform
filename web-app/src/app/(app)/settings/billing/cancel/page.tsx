"use client";

import Link from "next/link";

export default function BillingCancelPage() {
  return (
    <div className="mx-auto max-w-lg space-y-6 py-16 text-center">
      <h1 className="text-2xl font-semibold text-slate-900">
        Checkout canceled
      </h1>
      <p className="text-sm text-slate-600">
        No changes were made to your account. You can try upgrading again whenever you&apos;re ready.
      </p>
      <div className="flex justify-center gap-3">
        <Link
          href="/settings/billing"
          className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white"
        >
          Back to billing
        </Link>
      </div>
    </div>
  );
}
