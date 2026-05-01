"use client";

import { useState, useMemo, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppSidebar, type DashboardSection } from "@/components/app-sidebar";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type {
  DashboardData,
  DemographicRow,
  PhaseScopedData,
  Video,
} from "@/lib/dashboard-data";
import { DailyChart } from "@/components/daily-chart";
import { SubscribersChart } from "@/components/subscribers-chart";
import { NewSubsChart } from "@/components/new-subs-chart";
import { PeriodChart } from "@/components/period-chart";
import { PhaseSelector } from "@/components/phase-selector";
import { LoadingOverlay } from "@/components/loading-overlay";
import { aggregateDaily, deltaPct, type PeriodPoint } from "@/lib/aggregate";

function fmt(n: number) {
  return n.toLocaleString("en-US");
}
function usd(n: number) {
  return (
    "$" +
    n.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}
function pct(n: number) {
  return (n * 100).toFixed(1) + "%";
}
function cpvColor(cpv: number) {
  if (cpv <= 0.03) return "text-emerald-400";
  if (cpv <= 0.04) return "text-amber-400";
  return "text-red-400";
}

function VideoRow({ video, isBest }: { video: Video; isBest: boolean }) {
  const [expanded, setExpanded] = useState(true);
  return (
    <>
      <tr
        className="group cursor-pointer hover:bg-muted/30"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="py-3.5 px-4 font-semibold text-foreground text-sm">
          {video.name}
          {isBest && (
            <span className="ml-2 text-[10px] font-semibold text-emerald-400 border border-emerald-400/30 rounded px-1.5 py-0.5 align-middle">
              BEST
            </span>
          )}
          <span className="ml-2 text-muted-foreground text-xs">
            {expanded ? "▾" : "▸"}
          </span>
        </td>
        <td className="py-3.5 px-4 text-right text-sm tabular-nums">
          {fmt(video.views)}
        </td>
        <td className="py-3.5 px-4 text-right text-sm tabular-nums">
          {fmt(video.publicViews)}
        </td>
        <td className="py-3.5 px-4 text-right text-sm tabular-nums">
          {fmt(video.likes)}
        </td>
        <td className="py-3.5 px-4 text-right text-sm tabular-nums">
          {fmt(video.comments)}
        </td>
        <td className="py-3.5 px-4 text-right text-sm tabular-nums">
          {fmt(video.q25)}
        </td>
        <td className="py-3.5 px-4 text-right text-sm tabular-nums">
          {fmt(video.q50)}
        </td>
        <td className="py-3.5 px-4 text-right text-sm tabular-nums">
          {fmt(video.q75)}
        </td>
        <td className="py-3.5 px-4 text-right text-sm tabular-nums">
          {fmt(video.q100)}
        </td>
        <td className="py-3.5 px-4 text-right text-sm tabular-nums">
          {usd(video.cost)}
        </td>
        <td
          className={`py-3.5 px-4 text-right text-sm tabular-nums ${cpvColor(video.cpv)}`}
        >
          ${video.cpv.toFixed(2)}
        </td>
        <td className="py-3.5 px-4 text-right text-sm tabular-nums">
          {pct(video.viewRate)}
        </td>
      </tr>
      {expanded &&
        [...video.adGroups].sort((a, b) => b.views - a.views).map((ag) => (
          <tr
            key={ag.name}
            className="hover:bg-muted/20"
          >
            <td className="py-2.5 pl-10 pr-4 text-xs text-muted-foreground">
              {ag.name}
            </td>
            <td className="py-2.5 px-4 text-right text-xs text-muted-foreground tabular-nums">
              {fmt(ag.views)}
            </td>
            <td className="py-2.5 px-4 text-right text-xs text-muted-foreground" />
            <td className="py-2.5 px-4 text-right text-xs text-muted-foreground" />
            <td className="py-2.5 px-4 text-right text-xs text-muted-foreground" />
            <td className="py-2.5 px-4 text-right text-xs text-muted-foreground tabular-nums">
              {fmt(ag.q25)}
            </td>
            <td className="py-2.5 px-4 text-right text-xs text-muted-foreground tabular-nums">
              {fmt(ag.q50)}
            </td>
            <td className="py-2.5 px-4 text-right text-xs text-muted-foreground tabular-nums">
              {fmt(ag.q75)}
            </td>
            <td className="py-2.5 px-4 text-right text-xs text-muted-foreground tabular-nums">
              {fmt(ag.q100)}
            </td>
            <td className="py-2.5 px-4 text-right text-xs text-muted-foreground tabular-nums">
              {usd(ag.cost)}
            </td>
            <td
              className={`py-2.5 px-4 text-right text-xs tabular-nums ${cpvColor(ag.cpv)}`}
            >
              ${ag.cpv.toFixed(2)}
            </td>
            <td className="py-2.5 px-4 text-right text-xs text-muted-foreground tabular-nums">
              {pct(ag.viewRate)}
            </td>
          </tr>
        ))}
    </>
  );
}

export default function App({
  user,
  data: D,
}: {
  user: { name: string; email: string; image: string };
  data: DashboardData;
}) {
  const [active, setActive] = useState<DashboardSection>("views-daily");
  const headerLabelMap: Record<DashboardSection, string> = {
    "views-daily": "Daily Performance",
    "views-weekly": "Weekly Performance",
    "views-monthly": "Monthly Performance",
    "subscribers-overview": "Subscribers",
  };
  const headerLabel = headerLabelMap[active];

  // Phase selector state (only used by Views Daily Performance)
  const router = useRouter();
  const searchParams = useSearchParams();
  const phasesList = D.phases ?? [];
  const phaseFromUrl = searchParams.get("phase");
  const initialPhaseId =
    (phaseFromUrl && phasesList.some((p) => p.id === phaseFromUrl) ? phaseFromUrl : null) ??
    D.defaultPhaseId ??
    phasesList[0]?.id ??
    "";
  const [selectedPhaseId, setSelectedPhaseId] = useState(initialPhaseId);
  const [phaseData, setPhaseData] = useState<PhaseScopedData | null>(null);
  const [phaseLoading, setPhaseLoading] = useState(true);

  useEffect(() => {
    if (!selectedPhaseId) return;
    let cancelled = false;
    const run = async () => {
      setPhaseLoading(true);
      try {
        const r = await fetch(`/api/v1/dashboard/phase/${selectedPhaseId}`, {
          credentials: "include",
        });
        const data: PhaseScopedData | null = r.ok ? await r.json() : null;
        if (!cancelled) {
          setPhaseData(data);
          setPhaseLoading(false);
        }
      } catch {
        if (!cancelled) setPhaseLoading(false);
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, [selectedPhaseId]);

  const handlePhaseChange = (id: string) => {
    setSelectedPhaseId(id);
    const params = new URLSearchParams(searchParams.toString());
    params.set("phase", id);
    router.replace(`?${params.toString()}`, { scroll: false });
  };

  const phaseComputed = useMemo(() => {
    if (!phaseData) return null;
    const p = phaseData.phase;
    const totalViews = phaseData.totalPaidViews;
    const totalSpend = phaseData.totalSpend;
    const totalImpressions = phaseData.totalImpressions;
    const totalPublicViews = phaseData.totalPublicViews;
    const avgCPV = phaseData.avgCPV;
    const overallViewRate = totalImpressions > 0 ? totalViews / totalImpressions : 0;
    const budgetPct = p.budget > 0 ? (totalSpend / p.budget) * 100 : 0;

    const phaseStart = new Date(p.start + "T00:00:00");
    const phaseEnd = new Date(p.end + "T23:59:59");
    const now = new Date(phaseData.lastUpdated);
    const totalDays = Math.max(
      1,
      Math.ceil((phaseEnd.getTime() - phaseStart.getTime()) / (1000 * 60 * 60 * 24)),
    );
    const daysElapsed = Math.max(
      1,
      Math.min(
        totalDays,
        Math.ceil((now.getTime() - phaseStart.getTime()) / (1000 * 60 * 60 * 24)),
      ),
    );
    const daysRemaining = Math.max(0, totalDays - daysElapsed);
    const expectedPacePct = (daysElapsed / totalDays) * 100;
    const dailySpendRate = totalSpend / daysElapsed;
    const neededDailySpend =
      daysRemaining > 0 ? Math.max(0, p.budget - totalSpend) / daysRemaining : 0;
    const projectedPaidViews = phaseData.projectedPaidViews;
    const paceRatio = expectedPacePct > 0 ? budgetPct / expectedPacePct : 1;

    const fallback: Video = phaseData.videos[0] ?? {
      name: "",
      views: 0,
      cost: 0,
      cpv: 0,
      impressions: 0,
      viewRate: 0,
      publicViews: 0,
      likes: 0,
      comments: 0,
      q25: 0,
      q50: 0,
      q75: 0,
      q100: 0,
      adGroups: [],
    };
    const bestVideo = phaseData.videos.reduce(
      (best, v) =>
        v.views > best.views || (v.views === best.views && v.cpv < best.cpv) ? v : best,
      fallback,
    );
    const sortedVideos = [...phaseData.videos].sort((a, b) => b.views - a.views);

    const phaseEndShort = new Date(p.end + "T00:00:00").toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
    let statusClass = "bg-emerald-400/8 border-emerald-400/20 text-emerald-400";
    let statusMsg = `On track — projected ${fmt(projectedPaidViews)} paid views by ${phaseEndShort}`;
    let statusDetail = `${fmt(daysRemaining)} days left · ${usd(neededDailySpend)}/day needed`;
    if (paceRatio < 0.8) {
      statusClass = "bg-amber-400/8 border-amber-400/20 text-amber-400";
      statusMsg = `Underpacing — increase daily budget to ${usd(neededDailySpend)}/day`;
      statusDetail = `${fmt(daysRemaining)} days left · Currently spending ${usd(dailySpendRate)}/day`;
    } else if (paceRatio > 1.2) {
      statusClass = "bg-red-400/8 border-red-400/20 text-red-400";
      statusMsg = "Overpacing — budget will run out early at current rate";
      statusDetail = `${fmt(daysRemaining)} days left · Currently spending ${usd(dailySpendRate)}/day`;
    }
    const fillColor = () => {
      if (paceRatio > 1.15) return "bg-red-400";
      if (paceRatio < 0.85) return "bg-amber-400";
      return "bg-emerald-400";
    };

    return {
      phase: p,
      totalViews,
      totalSpend,
      totalImpressions,
      totalPublicViews,
      avgCPV,
      overallViewRate,
      budgetPct,
      daysRemaining,
      expectedPacePct,
      dailySpendRate,
      neededDailySpend,
      bestVideo,
      sortedVideos,
      projectedPaidViews,
      statusClass,
      statusMsg,
      statusDetail,
      fillColor,
      daily: phaseData.daily,
      demographics: phaseData.demographics,
      isInProgress: p.status === "in-progress",
      phaseEndShort,
    };
  }, [phaseData]);

  return (
    <SidebarProvider>
      <AppSidebar user={user} active={active} onSectionChange={setActive} />
      <SidebarInset>
        <header className="flex h-16 shrink-0 items-center gap-2 transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-12">
          <div className="flex items-center gap-2 px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator
              orientation="vertical"
              className="mr-2 data-[orientation=vertical]:h-4"
            />
            <h1 className="text-base font-medium">
              FOM <span className="text-emerald-400">{headerLabel}</span>
            </h1>
          </div>
          <div className="ml-auto flex items-center gap-3 pr-4 text-xs text-muted-foreground">
            <span>
              {active === "views-daily" && phaseComputed
                ? `${new Date(phaseComputed.phase.start + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })} – ${new Date(phaseComputed.phase.end + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`
                : `${new Date(D.flightStart + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })} – ${new Date(D.flightEnd + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}`}
              {" · Updated "}
              {new Date(D.lastUpdated).toLocaleDateString()}
            </span>
            {active === "views-daily" && phasesList.length > 0 && (
              <PhaseSelector
                phases={phasesList}
                value={selectedPhaseId}
                onChange={handlePhaseChange}
              />
            )}
          </div>
        </header>

        {active === "subscribers-overview" ? (
          <SubscribersSection data={D} />
        ) : active === "views-weekly" ? (
          <PeriodSection data={D} by="week" />
        ) : active === "views-monthly" ? (
          <PeriodSection data={D} by="month" />
        ) : phaseComputed ? (
        <div className="flex flex-col gap-4 p-4">
          {phaseLoading && <LoadingOverlay />}

          {phaseComputed.isInProgress && (
            <>
              {/* Status Banner */}
              <div
                className={`rounded-lg border px-6 py-3.5 text-sm font-medium flex justify-between items-center ${phaseComputed.statusClass}`}
              >
                <span>{phaseComputed.statusMsg}</span>
                <span className="text-xs font-normal opacity-80">
                  {phaseComputed.statusDetail}
                </span>
              </div>

              {/* Budget Bar */}
              <Card>
                <CardContent className="pt-5 pb-4">
                  <div className="flex justify-between mb-3 text-xs">
                    <span className="font-semibold">
                      {usd(phaseComputed.totalSpend)} spent ({phaseComputed.budgetPct.toFixed(1)}%)
                    </span>
                    <span className="text-muted-foreground">
                      ${fmt(phaseComputed.phase.budget)} {phaseComputed.phase.label} budget
                    </span>
                  </div>
                  <div className="relative w-full h-1 bg-muted rounded-full">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ease-out ${phaseComputed.fillColor()}`}
                      style={{ width: `${Math.min(phaseComputed.budgetPct, 100)}%` }}
                    />
                    <div
                      className="absolute -top-1 w-0.5 h-3 bg-muted-foreground rounded-sm"
                      style={{ left: `${Math.min(phaseComputed.expectedPacePct, 100)}%` }}
                      title="Expected pace"
                    />
                  </div>
                  <div className="flex justify-between mt-2 text-[10px] text-muted-foreground">
                    <span>{fmt(phaseComputed.daysRemaining)} days remaining</span>
                    <span>
                      {usd(phaseComputed.dailySpendRate)}/day avg · {usd(phaseComputed.neededDailySpend)}/day needed
                    </span>
                  </div>
                </CardContent>
              </Card>
            </>
          )}

          {/* Channel Stats */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                  Public Views
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold tabular-nums">
                  {fmt(phaseComputed.totalPublicViews)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Long-form videos only
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-[11px] uppercase tracking-wider text-emerald-400/70 font-medium">
                  {phaseComputed.isInProgress ? "Projected Paid Views" : "Final Paid Views"}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold tabular-nums">
                  {phaseComputed.isInProgress ? `~${fmt(phaseComputed.projectedPaidViews)}` : fmt(phaseComputed.totalViews)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {phaseComputed.isInProgress
                    ? `Projection by ${phaseComputed.phaseEndShort} at current pace`
                    : `${phaseComputed.phase.label} closed`}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                  Paid Views
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold tabular-nums">
                  {fmt(phaseComputed.totalViews)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {fmt(phaseComputed.totalImpressions)} impressions
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                  Avg CPV
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  className={`text-2xl font-semibold tabular-nums ${cpvColor(phaseComputed.avgCPV)}`}
                >
                  ${phaseComputed.avgCPV.toFixed(2)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Target: <span className="text-emerald-400">$0.02-$0.03</span>
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                  View Rate
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold tabular-nums">
                  {pct(phaseComputed.overallViewRate)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Views / Impressions
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                  Total Spend
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold tabular-nums">
                  {usd(phaseComputed.totalSpend)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {phaseComputed.isInProgress
                    ? `${usd(Math.max(0, phaseComputed.phase.budget - phaseComputed.totalSpend))} remaining`
                    : `${phaseComputed.phase.label} final`}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Daily Views Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
                Daily Views
              </CardTitle>
            </CardHeader>
            <CardContent>
              <DailyChart data={phaseComputed.daily} />
            </CardContent>
          </Card>

          {/* Per Video Table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
                Per Video
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left text-[10px] uppercase tracking-wider text-muted-foreground font-medium py-2.5 px-4">
                        Video / Ad Group
                      </th>
                      <th className="text-right text-[10px] uppercase tracking-wider text-muted-foreground font-medium py-2.5 px-4">
                        Paid Views
                      </th>
                      <th className="text-right text-[10px] uppercase tracking-wider text-muted-foreground font-medium py-2.5 px-4">
                        YT Views
                      </th>
                      <th className="text-right text-[10px] uppercase tracking-wider text-muted-foreground font-medium py-2.5 px-4">
                        Likes
                      </th>
                      <th className="text-right text-[10px] uppercase tracking-wider text-muted-foreground font-medium py-2.5 px-4">
                        Comments
                      </th>
                      <th className="text-right text-[10px] uppercase tracking-wider text-muted-foreground font-medium py-2.5 px-4">
                        25%
                      </th>
                      <th className="text-right text-[10px] uppercase tracking-wider text-muted-foreground font-medium py-2.5 px-4">
                        50%
                      </th>
                      <th className="text-right text-[10px] uppercase tracking-wider text-muted-foreground font-medium py-2.5 px-4">
                        75%
                      </th>
                      <th className="text-right text-[10px] uppercase tracking-wider text-muted-foreground font-medium py-2.5 px-4">
                        100%
                      </th>
                      <th className="text-right text-[10px] uppercase tracking-wider text-muted-foreground font-medium py-2.5 px-4">
                        Spend
                      </th>
                      <th className="text-right text-[10px] uppercase tracking-wider text-muted-foreground font-medium py-2.5 px-4">
                        CPV
                      </th>
                      <th className="text-right text-[10px] uppercase tracking-wider text-muted-foreground font-medium py-2.5 px-4">
                        View Rate
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {phaseComputed.sortedVideos.map((v) => (
                      <VideoRow
                        key={v.name}
                        video={v}
                        isBest={v === phaseComputed.bestVideo}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Demographics */}
          {phaseComputed.demographics && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {(
                [
                  ["Age", phaseComputed.demographics.age],
                  ["Gender", phaseComputed.demographics.gender],
                  ["Device", phaseComputed.demographics.device],
                  ["DMA Region", phaseComputed.demographics.geo],
                ] as [string, DemographicRow[]][]
              ).map(([title, rows]) => (
                <Card key={title}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                      {title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2.5">
                    {rows.map((row) => (
                      <div key={row.label} className="space-y-1">
                        <div className="flex justify-between text-xs">
                          <span className="text-foreground">{row.label}</span>
                          <span className="text-muted-foreground">
                            {fmt(row.views)} views · {pct(row.pctOfViews)}
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-muted/30 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-emerald-400/70"
                            style={{ width: `${Math.max(row.pctOfViews * 100, 1)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Footer */}
          <p className="text-center text-[10px] text-muted-foreground/40 py-4">
            Powered by Graphite
          </p>
        </div>
        ) : (
          <LoadingOverlay />
        )}
      </SidebarInset>
    </SidebarProvider>
  );
}

function SubscribersSection({ data: D }: { data: DashboardData }) {
  const sc = D.subscribersCampaign;
  if (!sc) {
    return (
      <div className="flex flex-col gap-4 p-4">
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No subscribers-campaign data yet. Once any &ldquo;FOM - Subscribers - *&rdquo;
            campaign starts spending, metrics will appear here.
          </CardContent>
        </Card>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Subscribers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold tabular-nums">
              {fmt(D.subscribers ?? 0)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Target: <span className="text-emerald-400">100K</span> in 12 months
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              New Subscribers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold tabular-nums">
              {fmt(sc.subsGained)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Since {new Date(sc.campaignStart + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Cost
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold tabular-nums">
              {usd(sc.cost)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Campaign spend
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Impressions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold tabular-nums">
              {fmt(sc.impressions)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Total served
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Cost per Subscriber
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold tabular-nums">
              {sc.subsGained > 0 ? usd(sc.costPerSub) : "—"}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Cost / new subs
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Conversion Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold tabular-nums">
              {sc.impressions > 0 ? (sc.convRate * 100).toFixed(3) + "%" : "—"}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Subs / impressions
            </p>
          </CardContent>
        </Card>
      </div>

      {D.subscriberHistory && D.subscriberHistory.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
              Subscribers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <SubscribersChart data={D.subscriberHistory} />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
            New Subscribers per Day
          </CardTitle>
        </CardHeader>
        <CardContent>
          {sc.daily.length > 0 ? (
            <NewSubsChart data={sc.daily} />
          ) : (
            <p className="py-10 text-center text-sm text-muted-foreground">
              No daily data yet for {sc.campaignStart} → today.
            </p>
          )}
        </CardContent>
      </Card>

      <p className="text-center text-[10px] text-muted-foreground/40 py-4">
        Powered by Graphite
      </p>
    </div>
  );
}

function deltaBadge(d: number | null) {
  if (d === null) return <span className="text-muted-foreground">—</span>;
  const pct = (d * 100).toFixed(1);
  const sign = d > 0 ? "+" : "";
  const cls = d > 0 ? "text-emerald-400" : d < 0 ? "text-red-400" : "text-muted-foreground";
  return <span className={cls}>{sign}{pct}%</span>;
}

function PeriodSection({
  data: D,
  by,
}: {
  data: DashboardData;
  by: "week" | "month";
}) {
  const periods = useMemo(
    () => aggregateDaily(D.daily, by, new Date(D.lastUpdated)),
    [D.daily, D.lastUpdated, by],
  );

  if (periods.length === 0) {
    return (
      <div className="flex flex-col gap-4 p-4">
        <Card>
          <CardContent className="py-10 text-center text-sm text-muted-foreground">
            No daily data to aggregate yet.
          </CardContent>
        </Card>
      </div>
    );
  }

  const latest: PeriodPoint = periods[periods.length - 1];
  const prior = periods.length > 1 ? periods[periods.length - 2] : null;
  const dViews = prior ? deltaPct(latest.views, prior.views) : null;
  const dCost = prior ? deltaPct(latest.cost, prior.cost) : null;
  const dCpv = prior ? deltaPct(latest.cpv, prior.cpv) : null;
  const periodLabel = by === "week" ? "Week" : "Month";

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Latest {periodLabel} · Paid Views
              {latest.isPartial && (
                <span className="ml-2 text-[10px] font-normal text-amber-400 normal-case">
                  partial
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold tabular-nums">
              {fmt(latest.views)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {latest.label} · {deltaBadge(dViews)} vs prior {by}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Latest {periodLabel} · Spend
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold tabular-nums">
              {usd(latest.cost)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {deltaBadge(dCost)} vs prior {by}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Latest {periodLabel} · Avg CPV
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-semibold tabular-nums ${cpvColor(latest.cpv)}`}>
              ${latest.cpv.toFixed(3)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {deltaBadge(dCpv)} vs prior {by}
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
            Paid Views per {periodLabel}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <PeriodChart data={periods} />
          <p className="mt-3 text-[10px] text-muted-foreground">
            Striped bar = current {by} (in progress). Hover for spend / CPV.
          </p>
        </CardContent>
      </Card>

      <p className="text-center text-[10px] text-muted-foreground/40 py-4">
        Powered by Graphite
      </p>
    </div>
  );
}
