import { useMemo, useState } from "react";
import { AppLayout } from "./components/layout/AppLayout";
import { EmptyPanel } from "./components/ui/EmptyPanel";
import type { Page } from "./domain/constants";
import { useAppData } from "./hooks/useAppData";
import { AddBottlePage } from "./pages/AddBottlePage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { BottleDetailPage } from "./pages/BottleDetailPage";
import { BottlesPage } from "./pages/BottlesPage";
import { CellarPage } from "./pages/CellarPage";
import { CollectionExplorerPage } from "./pages/CollectionExplorerPage";
import { CsvImportPage } from "./pages/CsvImportPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LabelIntakePage } from "./pages/LabelIntakePage";
import { RegistryQualityPage } from "./pages/RegistryQualityPage";
import { RegistrySearchPage } from "./pages/RegistrySearchPage";
import { TransactionsPage } from "./pages/TransactionsPage";

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [selectedBottleId, setSelectedBottleId] = useState<string | null>(null);
  const { data, loading, error, notice, refresh, afterMutation } = useAppData();

  const selectedBottle = useMemo(
    () => data.bottles.find((bottle) => bottle.id === selectedBottleId) ?? data.bottles[0],
    [data.bottles, selectedBottleId],
  );

  function openBottle(id: string) {
    setSelectedBottleId(id);
    setPage("detail");
  }

  return (
    <AppLayout
      page={page}
      setPage={setPage}
      error={error}
      notice={notice}
      loading={loading}
      refresh={refresh}
    >
      {page === "dashboard" && <DashboardPage data={data} openBottle={openBottle} />}
      {page === "analytics" && <AnalyticsPage />}
      {page === "collection" && <CollectionExplorerPage data={data} afterMutation={afterMutation} />}
      {page === "bottles" && <BottlesPage data={data} openBottle={openBottle} />}
      {page === "detail" && selectedBottle ? (
        <BottleDetailPage
          bottle={selectedBottle}
          locations={data.locations}
          transactions={data.transactions.filter((item) => item.bottle_id === selectedBottle.id)}
          afterMutation={afterMutation}
        />
      ) : page === "detail" ? (
        <EmptyPanel title="还没有藏酒" text="先从新增入库开始创建第一瓶酒。" />
      ) : null}
      {page === "add" && <AddBottlePage data={data} afterMutation={afterMutation} openBottle={openBottle} />}
      {page === "import" && <CsvImportPage afterMutation={afterMutation} openBottle={openBottle} />}
      {page === "registry-search" && <RegistrySearchPage />}
      {page === "registry" && <RegistryQualityPage />}
      {page === "label" && <LabelIntakePage data={data} afterMutation={afterMutation} openBottle={openBottle} />}
      {page === "cellar" && <CellarPage data={data} openBottle={openBottle} afterMutation={afterMutation} />}
      {page === "transactions" && <TransactionsPage data={data} afterMutation={afterMutation} />}
    </AppLayout>
  );
}
