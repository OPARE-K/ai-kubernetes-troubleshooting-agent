"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/contexts/AuthContext";

export default function HomePage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    router.replace(user ? "/dashboard" : "/login");
  }, [user, isLoading, router]);

  return (
    <main className="app-background flex min-h-screen flex-col items-center justify-center gap-4 text-slate-300">
      <span className="h-10 w-10 animate-spin rounded-full border-2 border-sky-500/30 border-t-sky-400" />
      <p className="text-sm text-slate-400">Loading...</p>
    </main>
  );
}
