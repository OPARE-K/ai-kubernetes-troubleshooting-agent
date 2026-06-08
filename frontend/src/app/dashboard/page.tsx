"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Dashboard } from "@/components/Dashboard";
import { useAuth } from "@/contexts/AuthContext";

export default function DashboardPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  if (isLoading || !user) {
    return (
      <main className="app-background flex min-h-screen flex-col items-center justify-center gap-4 text-slate-300">
        <span className="h-10 w-10 animate-spin rounded-full border-2 border-sky-500/30 border-t-sky-400" />
        <p className="text-sm text-slate-400">Loading dashboard...</p>
      </main>
    );
  }

  return <Dashboard />;
}
