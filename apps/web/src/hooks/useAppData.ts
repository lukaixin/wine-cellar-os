import { useEffect, useState } from "react";
import { api } from "../api";
import type { AppData } from "../types";

const emptyData: AppData = {
  producers: [],
  wines: [],
  vintages: [],
  cellars: [],
  locations: [],
  bottles: [],
  transactions: [],
};

export function useAppData() {
  const [data, setData] = useState<AppData>(emptyData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [dashboard, producers, wines, vintages, cellars, locations, bottles, transactions] = await Promise.all([
        api.dashboard(),
        api.producers(),
        api.wines(),
        api.vintages(),
        api.cellars(),
        api.locations(),
        api.bottles(),
        api.transactions(),
      ]);
      setData({ dashboard, producers, wines, vintages, cellars, locations, bottles, transactions });
    } catch (err) {
      setError(err instanceof Error ? err.message : "无法连接本地 API");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function afterMutation(message: string) {
    setNotice(message);
    await refresh();
  }

  return {
    data,
    error,
    loading,
    notice,
    refresh,
    afterMutation,
    setNotice,
  };
}
