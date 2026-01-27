"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/format";

type TabType = "receivables" | "payables";

export default function ReceivablesPage() {
    const [activeTab, setActiveTab] = useState<TabType>("receivables");
    const queryClient = useQueryClient();

    const receivablesQuery = useQuery({
        queryKey: ["analytics-receivables"],
        queryFn: () => api.analytics.receivables(),
    });

    const payablesQuery = useQuery({
        queryKey: ["analytics-payables"],
        queryFn: () => api.analytics.payables(),
    });

    const receivablesListQuery = useQuery({
        queryKey: ["receivables-list"],
        queryFn: () => api.analytics.receivablesList(),
        enabled: activeTab === "receivables",
    });

    const payablesListQuery = useQuery({
        queryKey: ["payables-list"],
        queryFn: () => api.analytics.payablesList(),
        enabled: activeTab === "payables",
    });

    const togglePaymentMutation = useMutation({
        mutationFn: async ({ id, type, status }: { id: number; type: "journal" | "transaction"; status: "paid" | "unpaid" }) => {
            if (type === "transaction") {
                return api.analytics.toggleTransactionPayment(id, status);
            } else {
                return api.analytics.toggleJournalPayment(id, status);
            }
        },
        onSuccess: () => {
            toast.success("Payment status updated");
            // Refresh all AR/AP data
            queryClient.invalidateQueries({ queryKey: ["analytics-receivables"] });
            queryClient.invalidateQueries({ queryKey: ["analytics-payables"] });
            queryClient.invalidateQueries({ queryKey: ["receivables-list"] });
            queryClient.invalidateQueries({ queryKey: ["payables-list"] });
        },
        onError: (error) => {
            toast.error(error instanceof Error ? error.message : "Failed to update payment status");
        },
    });

    const items = activeTab === "receivables" ? receivablesListQuery.data : payablesListQuery.data;
    const isLoading = activeTab === "receivables" ? receivablesListQuery.isLoading : payablesListQuery.isLoading;

    const handleMarkAsPaid = (id: number, type: "journal" | "transaction") => {
        togglePaymentMutation.mutate({ id, type, status: "paid" });
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <header>
                <h1 className="text-2xl font-semibold text-slate-900">Receivables & Payables</h1>
                <p className="text-sm text-slate-500 mt-1">
                    Track money owed to you and money you owe
                </p>
            </header>

            {/* Summary Cards */}
            <div className="grid gap-4 sm:grid-cols-2">
                <button
                    onClick={() => setActiveTab("receivables")}
                    className={`rounded-xl border p-6 text-left transition-all ${activeTab === "receivables"
                        ? "border-blue-500 bg-blue-50 ring-2 ring-blue-200"
                        : "bg-white hover:border-slate-300"
                        }`}
                >
                    <div className="flex items-center justify-between mb-2">
                        <h3 className="font-semibold text-slate-900">Accounts Receivable</h3>
                        <span className="text-xs text-slate-500">Money owed to you</span>
                    </div>
                    <span className="text-3xl font-bold text-blue-600">
                        {formatCurrency(receivablesQuery.data?.total ?? 0)}
                    </span>
                    {(receivablesQuery.data?.count ?? 0) > 0 && (
                        <span className="ml-2 text-sm text-slate-500">
                            ({receivablesQuery.data?.count} unpaid)
                        </span>
                    )}
                </button>

                <button
                    onClick={() => setActiveTab("payables")}
                    className={`rounded-xl border p-6 text-left transition-all ${activeTab === "payables"
                        ? "border-orange-500 bg-orange-50 ring-2 ring-orange-200"
                        : "bg-white hover:border-slate-300"
                        }`}
                >
                    <div className="flex items-center justify-between mb-2">
                        <h3 className="font-semibold text-slate-900">Accounts Payable</h3>
                        <span className="text-xs text-slate-500">Money you owe</span>
                    </div>
                    <span className="text-3xl font-bold text-orange-600">
                        {formatCurrency(payablesQuery.data?.total ?? 0)}
                    </span>
                    {(payablesQuery.data?.count ?? 0) > 0 && (
                        <span className="ml-2 text-sm text-slate-500">
                            ({payablesQuery.data?.count} unpaid)
                        </span>
                    )}
                </button>
            </div>

            {/* List Section */}
            <div className="rounded-xl border bg-white shadow-sm">
                <div className="border-b px-6 py-4">
                    <h3 className="font-semibold text-slate-900">
                        {activeTab === "receivables" ? "Unpaid Revenue" : "Unpaid Expenses"}
                    </h3>
                    <p className="text-sm text-slate-500">
                        {activeTab === "receivables"
                            ? "Sales and income that haven't been collected yet"
                            : "Bills and expenses that haven't been paid yet"}
                    </p>
                </div>

                {isLoading ? (
                    <div className="p-6 text-center text-slate-500">Loading...</div>
                ) : !items || items.length === 0 ? (
                    <div className="p-12 text-center">
                        <div className="text-4xl mb-4">
                            {activeTab === "receivables" ? "💰" : "📄"}
                        </div>
                        <p className="text-slate-600 font-medium">
                            {activeTab === "receivables"
                                ? "No unpaid receivables"
                                : "No unpaid payables"}
                        </p>
                        <p className="text-sm text-slate-500 mt-1">
                            {activeTab === "receivables"
                                ? "All your revenue has been collected!"
                                : "All your bills have been paid!"}
                        </p>
                    </div>
                ) : (
                    <ul className="divide-y">
                        {items.map((item) => (
                            <li
                                key={`${item.type}-${item.id}`}
                                className="flex items-center justify-between px-6 py-4 hover:bg-slate-50"
                            >
                                <div className="flex-1 min-w-0">
                                    <p className="font-medium text-slate-900 truncate">
                                        {item.description}
                                    </p>
                                    <div className="flex items-center gap-2 mt-1">
                                        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                                            {item.category}
                                        </span>
                                        <span className="text-xs text-slate-500">
                                            {item.type === "journal" ? "📝 Journal" : "📊 Excel"}
                                        </span>
                                        {item.date && (
                                            <span className="text-xs text-slate-400">
                                                {new Date(item.date).toLocaleDateString()}
                                            </span>
                                        )}
                                    </div>
                                </div>

                                <div className="flex items-center gap-4">
                                    <span className={`font-semibold ${activeTab === "receivables" ? "text-blue-600" : "text-orange-600"
                                        }`}>
                                        {formatCurrency(item.amount)}
                                    </span>
                                    <Button
                                        size="sm"
                                        variant="outline"
                                        onClick={() => handleMarkAsPaid(item.id, item.type)}
                                        disabled={togglePaymentMutation.isPending}
                                    >
                                        ✓ Mark Paid
                                    </Button>
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}
