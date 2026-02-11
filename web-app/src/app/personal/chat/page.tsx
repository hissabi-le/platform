"use client";

import { useState, useRef, useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { PersonalInsights } from "@/lib/api";
import Link from "next/link";

type Message = {
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
};

const SUGGESTED_QUESTIONS = [
    "How much did I spend on dining this month?",
    "What are my top spending categories?",
    "Give me budgeting advice for next month",
    "How can I save more money?",
    "Compare my income vs expenses",
];

export default function PersonalChatPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Fetch insights for context display
    const { data: insights } = useQuery({
        queryKey: ["personal", "insights"],
        queryFn: () => api.personal.getInsights(),
    });

    // Chat mutation
    const chatMutation = useMutation({
        mutationFn: (message: string) => api.personal.chat(message),
        onSuccess: (data) => {
            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    content: data.response,
                    timestamp: new Date(),
                },
            ]);
        },
        onError: () => {
            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    content: "Sorry, I encountered an error. Please try again.",
                    timestamp: new Date(),
                },
            ]);
        },
    });

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = () => {
        if (!input.trim()) return;

        const userMessage: Message = {
            role: "user",
            content: input.trim(),
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        chatMutation.mutate(input.trim());
        setInput("");
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleSuggestionClick = (question: string) => {
        setInput(question);
    };

    const formatCurrency = (amount: number) =>
        new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(amount);

    return (
        <div className="flex flex-col h-[calc(100vh-7rem)] sm:h-[calc(100vh-8rem)]">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 sm:gap-4 mb-3 sm:mb-4">
                <div>
                    <h1 className="text-xl sm:text-2xl font-bold">AI Financial Assistant</h1>
                    <p className="text-muted-foreground text-sm">
                        Ask questions about your spending, get budgeting advice
                    </p>
                </div>
                <Link
                    href="/personal"
                    className="px-4 py-2 bg-secondary rounded-lg text-sm font-medium hover:bg-secondary/80 transition-colors self-start sm:self-auto"
                >
                    ← Back
                </Link>
            </div>

            {/* Context Card */}
            {insights && (
                <div className="bg-secondary/30 rounded-xl p-4 mb-4 flex flex-wrap gap-4 text-sm">
                    <div>
                        <span className="text-muted-foreground">This month: </span>
                        <span className="font-medium text-green-600">
                            +{formatCurrency(insights.this_month_income)}
                        </span>
                        {" / "}
                        <span className="font-medium text-red-500">
                            -{formatCurrency(insights.this_month_expense)}
                        </span>
                    </div>
                    <div>
                        <span className="text-muted-foreground">Net: </span>
                        <span
                            className={`font-medium ${insights.this_month_net >= 0 ? "text-green-600" : "text-red-500"
                                }`}
                        >
                            {formatCurrency(insights.this_month_net)}
                        </span>
                    </div>
                    {insights.top_category && (
                        <div>
                            <span className="text-muted-foreground">Top category: </span>
                            <span className="font-medium capitalize">{insights.top_category}</span>
                        </div>
                    )}
                </div>
            )}

            {/* Chat Messages */}
            <div className="flex-1 bg-card rounded-xl border p-4 overflow-y-auto mb-4">
                {messages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center">
                        <p className="text-4xl mb-4">💬</p>
                        <h3 className="text-lg font-semibold mb-2">Start a Conversation</h3>
                        <p className="text-muted-foreground mb-6 max-w-sm">
                            Ask me anything about your personal finances, spending patterns, or get budgeting advice.
                        </p>

                        {/* Suggested Questions */}
                        <div className="flex flex-wrap justify-center gap-2 max-w-lg">
                            {SUGGESTED_QUESTIONS.map((question, i) => (
                                <button
                                    key={i}
                                    onClick={() => handleSuggestionClick(question)}
                                    className="px-3 py-2 bg-secondary text-sm rounded-lg hover:bg-secondary/80 transition-colors text-left"
                                >
                                    {question}
                                </button>
                            ))}
                        </div>
                    </div>
                ) : (
                    <div className="space-y-4">
                        {messages.map((msg, i) => (
                            <div
                                key={i}
                                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                            >
                                <div
                                    className={`max-w-[80%] rounded-2xl px-4 py-3 ${msg.role === "user"
                                        ? "bg-primary text-primary-foreground"
                                        : "bg-secondary"
                                        }`}
                                >
                                    <p className="whitespace-pre-wrap">{msg.content}</p>
                                    <p
                                        className={`text-xs mt-1 ${msg.role === "user"
                                            ? "text-primary-foreground/70"
                                            : "text-muted-foreground"
                                            }`}
                                    >
                                        {msg.timestamp.toLocaleTimeString([], {
                                            hour: "2-digit",
                                            minute: "2-digit",
                                        })}
                                    </p>
                                </div>
                            </div>
                        ))}

                        {chatMutation.isPending && (
                            <div className="flex justify-start">
                                <div className="bg-secondary rounded-2xl px-4 py-3">
                                    <div className="flex gap-1">
                                        <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" />
                                        <span
                                            className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
                                            style={{ animationDelay: "0.1s" }}
                                        />
                                        <span
                                            className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce"
                                            style={{ animationDelay: "0.2s" }}
                                        />
                                    </div>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="flex gap-2 sm:gap-3">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask about your finances..."
                    className="flex-1 min-w-0 px-3 sm:px-4 py-3 border rounded-xl bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm sm:text-base"
                    disabled={chatMutation.isPending}
                />
                <button
                    onClick={handleSend}
                    disabled={chatMutation.isPending || !input.trim()}
                    className="px-4 sm:px-6 py-3 bg-primary text-primary-foreground rounded-xl font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 flex-shrink-0 text-sm sm:text-base"
                >
                    Send
                </button>
            </div>
        </div>
    );
}
