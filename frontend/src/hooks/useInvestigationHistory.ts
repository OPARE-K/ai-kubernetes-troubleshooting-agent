"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/contexts/AuthContext";
import { insforge } from "@/lib/insforge";
import type { InvestigationRecord } from "@/types/api";

export function useInvestigationHistory() {
  const { user } = useAuth();
  const [history, setHistory] = useState<InvestigationRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadHistory = useCallback(async () => {
    if (!user) {
      setHistory([]);
      return;
    }

    setIsLoading(true);
    const { data, error } = await insforge.database
      .from("investigations")
      .select("id, user_id, root_cause, namespace, confidence, status, created_at")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false })
      .limit(10);

    setIsLoading(false);
    if (error) {
      console.warn("Failed to load investigation history:", error.message);
      return;
    }
    setHistory((data as InvestigationRecord[]) ?? []);
  }, [user]);

  useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  return { history, isLoading, reloadHistory: loadHistory };
}
