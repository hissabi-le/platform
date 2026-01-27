// Alert component for notifications and errors
import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

type AlertVariant = "default" | "destructive" | "success" | "warning";

interface AlertProps {
    variant?: AlertVariant;
    title?: string;
    children: ReactNode;
    className?: string;
    onRetry?: () => void;
}

const variantStyles: Record<AlertVariant, string> = {
    default: "bg-slate-50 border-slate-200 text-slate-800",
    destructive: "bg-red-50 border-red-200 text-red-800",
    success: "bg-emerald-50 border-emerald-200 text-emerald-800",
    warning: "bg-amber-50 border-amber-200 text-amber-800",
};

const titleStyles: Record<AlertVariant, string> = {
    default: "text-slate-900",
    destructive: "text-red-900",
    success: "text-emerald-900",
    warning: "text-amber-900",
};

const buttonStyles: Record<AlertVariant, string> = {
    default: "text-slate-700 hover:text-slate-900",
    destructive: "text-red-700 hover:text-red-900",
    success: "text-emerald-700 hover:text-emerald-900",
    warning: "text-amber-700 hover:text-amber-900",
};

export function Alert({
    variant = "default",
    title,
    children,
    className,
    onRetry
}: AlertProps) {
    return (
        <div
            role="alert"
            className={cn(
                "rounded-lg border p-4",
                variantStyles[variant],
                className
            )}
        >
            {title && (
                <p className={cn("text-sm font-medium mb-1", titleStyles[variant])}>
                    {title}
                </p>
            )}
            <div className="text-sm">{children}</div>
            {onRetry && (
                <button
                    onClick={onRetry}
                    className={cn(
                        "mt-2 text-sm underline hover:no-underline",
                        buttonStyles[variant]
                    )}
                >
                    Try again
                </button>
            )}
        </div>
    );
}

// Convenience export for error display
interface ErrorAlertProps {
    error: Error | unknown;
    onRetry?: () => void;
}

export function ErrorAlert({ error, onRetry }: ErrorAlertProps) {
    const rawMessage = error instanceof Error ? error.message : "";

    // Provide user-friendly messages for common error types
    let title = "Something went wrong";
    let message = "An unexpected error occurred.";

    if (rawMessage.includes("fetch") || rawMessage.includes("network") || rawMessage.includes("Failed to fetch")) {
        title = "Unable to connect";
        message = "Please check your internet connection and make sure the server is running.";
    } else if (rawMessage.includes("401") || rawMessage.includes("Unauthorized")) {
        title = "Session expired";
        message = "Please sign in again to continue.";
    } else if (rawMessage.includes("404")) {
        title = "Not found";
        message = "The requested data doesn't exist yet.";
    } else if (error instanceof Error && error.message) {
        message = error.message;
    }

    return (
        <Alert variant="destructive" title={title} onRetry={onRetry}>
            {message}
        </Alert>
    );
}
