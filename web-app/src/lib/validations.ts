// Form validation schemas using Zod
import { z } from "zod";

// Login form validation
export const loginSchema = z.object({
    email: z
        .string()
        .min(1, "Email is required")
        .email("Please enter a valid email address"),
    password: z
        .string()
        .min(1, "Password is required")
        .min(6, "Password must be at least 6 characters"),
});

export type LoginFormData = z.infer<typeof loginSchema>;

// Organisation settings validation
export const orgSettingsSchema = z.object({
    total_initial_investment: z
        .string()
        .refine((val) => !isNaN(Number(val)), "Must be a valid number")
        .refine((val) => Number(val) >= 0, "Cannot be negative"),
    starting_cash_balance: z
        .string()
        .refine((val) => !isNaN(Number(val)), "Must be a valid number"),
    current_assets_value: z
        .string()
        .refine((val) => !isNaN(Number(val)), "Must be a valid number")
        .refine((val) => Number(val) >= 0, "Cannot be negative"),
    default_currency: z
        .string()
        .min(3, "Currency code must be 3 characters")
        .max(3, "Currency code must be 3 characters")
        .toUpperCase(),
    default_locale: z
        .string()
        .min(2, "Locale is required"),
});

export type OrgSettingsFormData = z.infer<typeof orgSettingsSchema>;

// Journal entry validation
export const journalEntrySchema = z.object({
    raw_text: z
        .string()
        .min(1, "Please enter at least one line")
        .max(10000, "Journal entry is too long"),
    date: z
        .string()
        .regex(/^\d{4}-\d{2}-\d{2}$/, "Invalid date format"),
});

export type JournalEntryFormData = z.infer<typeof journalEntrySchema>;

// Resolution draft validation
export const resolutionSchema = z.object({
    entry_id: z.number().nullable().optional(),
    treat_as_inventory: z.enum(["inventory", "expense"]),
    quantity: z.string().optional(),
    unit: z.string().optional(),
    unit_cost: z.string().optional(),
});

export type ResolutionFormData = z.infer<typeof resolutionSchema>;

// Helper to validate form data
export function validateForm<T>(
    schema: z.ZodSchema<T>,
    data: unknown
): { success: true; data: T } | { success: false; errors: Record<string, string> } {
    const result = schema.safeParse(data);

    if (result.success) {
        return { success: true, data: result.data };
    }

    const errors: Record<string, string> = {};
    result.error.issues.forEach((issue) => {
        const path = issue.path.join(".") || "form";
        if (!errors[path]) {
            errors[path] = issue.message;
        }
    });

    return { success: false, errors };
}
