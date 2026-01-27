// Loading skeleton components for better perceived performance
import { cn } from "@/lib/utils";
import type { CSSProperties } from "react";

interface SkeletonProps {
    className?: string;
    style?: CSSProperties;
}

export function Skeleton({ className, style }: SkeletonProps) {
    return (
        <div
            className={cn(
                "animate-pulse rounded-md bg-slate-200",
                className
            )}
            style={style}
        />
    );
}

export function CardSkeleton() {
    return (
        <div className="rounded-xl border bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-2 w-2 rounded-full" />
            </div>
            <Skeleton className="h-8 w-24" />
        </div>
    );
}

export function TableRowSkeleton({ columns = 5 }: { columns?: number }) {
    return (
        <tr className="border-t">
            {Array.from({ length: columns }).map((_, i) => (
                <td key={i} className="px-4 py-3">
                    <Skeleton className="h-4 w-full" />
                </td>
            ))}
        </tr>
    );
}

export function TableSkeleton({ rows = 5, columns = 5 }: { rows?: number; columns?: number }) {
    return (
        <div className="overflow-hidden rounded-xl border bg-white shadow-sm">
            <table className="w-full text-sm">
                <thead>
                    <tr className="text-left text-xs uppercase text-gray-500">
                        {Array.from({ length: columns }).map((_, i) => (
                            <th key={i} className="px-4 py-3">
                                <Skeleton className="h-3 w-16" />
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {Array.from({ length: rows }).map((_, i) => (
                        <TableRowSkeleton key={i} columns={columns} />
                    ))}
                </tbody>
            </table>
        </div>
    );
}

const CHART_HEIGHTS = ["h-32", "h-48", "h-40", "h-56", "h-36", "h-44"];

export function ChartSkeleton() {
    return (
        <div className="rounded-xl border bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
                <Skeleton className="h-4 w-32" />
            </div>
            <div className="flex items-end gap-4 h-64">
                {CHART_HEIGHTS.map((height, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-2">
                        <Skeleton className={`w-full rounded-t ${height}`} />
                        <Skeleton className="h-3 w-12" />
                    </div>
                ))}
            </div>
        </div>
    );
}

export function PageSkeleton() {
    return (
        <div className="space-y-6">
            <div className="space-y-2">
                <Skeleton className="h-8 w-48" />
                <Skeleton className="h-4 w-96" />
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <CardSkeleton />
                <CardSkeleton />
                <CardSkeleton />
                <CardSkeleton />
            </div>
            <ChartSkeleton />
        </div>
    );
}
