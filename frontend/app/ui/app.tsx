"use client";

import { useState, useMemo } from "react";
import { AppSidebar } from "@/components/app-sidebar";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardData, Video } from "@/lib/dashboard-data";
import { DailyChart } from "@/components/daily-chart";
import { SubscribersChart } from "@/components/subscribers-chart";

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
        video.adGroups.map((ag) => (
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
  const computed = useMemo(() => {
    const totalViews = D.videos.reduce((s, v) => s + v.views, 0);
    const totalSpend = D.videos.reduce((s, v) => s + v.cost, 0);
    const totalImpressions = D.videos.reduce((s, v) => s + v.impressions, 0);
    const totalPublicViews = D.videos.reduce((s, v) => s + v.publicViews, 0);
    const avgCPV = totalViews > 0 ? totalSpend / totalViews : 0;
    const overallViewRate = totalImpressions > 0 ? totalViews / totalImpressions : 0;
    const budgetPct = D.budget > 0 ? (totalSpend / D.budget) * 100 : 0;

    const flightStart = new Date(D.flightStart + "T00:00:00");
    const flightEnd = new Date(D.flightEnd + "T23:59:59");
    const now = new Date(D.lastUpdated);
    const totalDays = Math.ceil(
      (flightEnd.getTime() - flightStart.getTime()) / (1000 * 60 * 60 * 24)
    );
    const daysElapsed = Math.max(
      1,
      Math.ceil(
        (now.getTime() - flightStart.getTime()) / (1000 * 60 * 60 * 24)
      )
    );
    const daysRemaining = Math.max(0, totalDays - daysElapsed);
    const expectedPacePct = totalDays > 0 ? (daysElapsed / totalDays) * 100 : 0;
    const dailySpendRate = totalSpend / daysElapsed;
    const neededDailySpend =
      daysRemaining > 0 ? (D.budget - totalSpend) / daysRemaining : 0;
    const projectedPublicViews =
      daysRemaining > 0
        ? Math.round(
            totalPublicViews + (totalPublicViews / daysElapsed) * daysRemaining
          )
        : totalPublicViews;

    const paceRatio = expectedPacePct > 0 ? budgetPct / expectedPacePct : 1;
    const bestVideo = D.videos.reduce(
      (best, v) =>
        v.views > best.views || (v.views === best.views && v.cpv < best.cpv)
          ? v
          : best,
      D.videos[0]
    );
    const sortedVideos = [...D.videos].sort((a, b) => b.views - a.views);

    let statusClass: string;
    let statusMsg: string;
    let statusDetail: string;
    if (paceRatio >= 0.85 && paceRatio <= 1.15) {
      statusClass =
        "bg-emerald-400/8 border-emerald-400/20 text-emerald-400";
      statusMsg = `On track — projected ${fmt(projectedPublicViews)} public views by Apr 30`;
      statusDetail = `${fmt(daysRemaining)} days left · ${usd(neededDailySpend)}/day needed`;
    } else if (paceRatio < 0.85) {
      statusClass = "bg-amber-400/8 border-amber-400/20 text-amber-400";
      statusMsg = `Underpacing — increase daily budget to ${usd(neededDailySpend)}/day`;
      statusDetail = `${fmt(daysRemaining)} days left · Currently spending ${usd(dailySpendRate)}/day`;
    } else {
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
      statusClass,
      statusMsg,
      statusDetail,
      fillColor,
    };
  }, [D]);

  const {
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
    statusClass,
    statusMsg,
    statusDetail,
    fillColor,
  } = computed;

  return (
    <SidebarProvider>
      <AppSidebar user={user} />
      <SidebarInset>
        <header className="flex h-16 shrink-0 items-center gap-2 transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-12">
          <div className="flex items-center gap-2 px-4">
            <SidebarTrigger className="-ml-1" />
            <Separator
              orientation="vertical"
              className="mr-2 data-[orientation=vertical]:h-4"
            />
            <h1 className="text-base font-medium">
              FOM <span className="text-emerald-400">YouTube Ads</span>
            </h1>
          </div>
          <div className="ml-auto pr-4 text-xs text-muted-foreground">
            {new Date(D.flightStart + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })} – {new Date(D.flightEnd + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })} · Updated{" "}
            {new Date(D.lastUpdated).toLocaleDateString()}
          </div>
        </header>

        <div className="flex flex-col gap-4 p-4">
          {/* Status Banner */}
          <div
            className={`rounded-lg border px-6 py-3.5 text-sm font-medium flex justify-between items-center ${statusClass}`}
          >
            <span>{statusMsg}</span>
            <span className="text-xs font-normal opacity-80">
              {statusDetail}
            </span>
          </div>

          {/* Budget Bar */}
          <Card>
            <CardContent className="pt-5 pb-4">
              <div className="flex justify-between mb-3 text-xs">
                <span className="font-semibold">
                  {usd(totalSpend)} spent ({budgetPct.toFixed(1)}%)
                </span>
                <span className="text-muted-foreground">
                  ${fmt(D.budget)} monthly budget
                </span>
              </div>
              <div className="relative w-full h-1 bg-muted rounded-full">
                <div
                  className={`h-full rounded-full transition-all duration-700 ease-out ${fillColor()}`}
                  style={{ width: `${Math.min(budgetPct, 100)}%` }}
                />
                <div
                  className="absolute -top-1 w-0.5 h-3 bg-muted-foreground rounded-sm"
                  style={{ left: `${Math.min(expectedPacePct, 100)}%` }}
                  title="Expected pace"
                />
              </div>
              <div className="flex justify-between mt-2 text-[10px] text-muted-foreground">
                <span>{fmt(daysRemaining)} days remaining</span>
                <span>
                  {usd(dailySpendRate)}/day avg · {usd(neededDailySpend)}
                  /day needed
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Channel Stats */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
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
                  Total Channel Views
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold tabular-nums">
                  {fmt(D.totalChannelViews ?? 0)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  All videos combined
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-[11px] uppercase tracking-wider text-emerald-400/70 font-medium">
                  Projected Paid Views
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold tabular-nums">
                  ~{fmt(D.projectedPaidViews ?? 0)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Projection by {new Date(D.flightEnd + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })} at current pace
                </p>
              </CardContent>
            </Card>
          </div>

          {/* KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                  Paid Views
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold tabular-nums">
                  {fmt(totalViews)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {fmt(totalImpressions)} impressions
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                  Public Views
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-semibold tabular-nums">
                  {fmt(totalPublicViews)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Lifetime views on YouTube
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
                  className={`text-2xl font-semibold tabular-nums ${cpvColor(avgCPV)}`}
                >
                  ${avgCPV.toFixed(2)}
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
                  {pct(overallViewRate)}
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
                  {usd(totalSpend)}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {usd(D.budget - totalSpend)} remaining
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
              <DailyChart data={D.daily} />
            </CardContent>
          </Card>

          {/* Subscribers Chart */}
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
                    {sortedVideos.map((v) => (
                      <VideoRow
                        key={v.name}
                        video={v}
                        isBest={v === bestVideo}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Footer */}
          <p className="text-center text-[10px] text-muted-foreground/40 py-4">
            Powered by Graphite
          </p>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
