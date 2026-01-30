// Shared stat card component for consistent KPI display
interface StatCardProps {
    title: string;
    value: string;
    accent?: string;
    subtitle?: string;
    trend?: "up" | "down" | "neutral";
    trendValue?: string;
}

export function StatCard({
    title,
    value,
    accent = "bg-muted-foreground",
    subtitle,
    trend,
    trendValue
}: StatCardProps) {
    return (
        <div className="rounded-xl border border-border bg-card text-card-foreground p-5 shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300">
            <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span className="font-medium">{title}</span>
                <span className={`h-2.5 w-2.5 rounded-full ${accent}`} aria-hidden="true" />
            </div>
            <div className="mt-3 text-2xl font-bold text-foreground">{value}</div>
            {(subtitle || (trend && trendValue)) && (
                <div className="mt-2 flex items-center gap-2">
                    {trend && trendValue && (
                        <span className={`inline-flex items-center text-xs font-medium ${trend === "up" ? "text-emerald-500" :
                            trend === "down" ? "text-red-500" :
                                "text-muted-foreground"
                            }`}>
                            {trend === "up" && (
                                <svg className="w-3 h-3 mr-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                                </svg>
                            )}
                            {trend === "down" && (
                                <svg className="w-3 h-3 mr-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                                </svg>
                            )}
                            {trendValue}
                        </span>
                    )}
                    {subtitle && <span className="text-xs text-muted-foreground">{subtitle}</span>}
                </div>
            )}
        </div>
    );
}
