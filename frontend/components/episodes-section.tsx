"use client";

import Image from "next/image";
import { Card } from "@/components/ui/card";
import type { Episode } from "@/lib/dashboard-data";

function fmtViews(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M views`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n >= 10_000 ? 0 : 1)}K views`;
  return `${n.toLocaleString("en-US")} views`;
}

function fmtDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function fmtPublishedAgo(iso: string): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  const now = Date.now();
  const days = Math.floor((now - then) / (1000 * 60 * 60 * 24));
  if (days < 1) return "today";
  if (days < 7) return `${days} day${days === 1 ? "" : "s"} ago`;
  if (days < 30) {
    const weeks = Math.floor(days / 7);
    return `${weeks} week${weeks === 1 ? "" : "s"} ago`;
  }
  if (days < 365) {
    const months = Math.floor(days / 30);
    return `${months} month${months === 1 ? "" : "s"} ago`;
  }
  const years = Math.floor(days / 365);
  return `${years} year${years === 1 ? "" : "s"} ago`;
}

export function EpisodesSection({ episodes }: { episodes: Episode[] }) {
  if (episodes.length === 0) {
    return (
      <div className="flex flex-col gap-4 p-4">
        <Card>
          <div className="py-10 text-center text-sm text-muted-foreground">
            No episodes yet. Once videos appear on the channel, they&apos;ll show here.
          </div>
        </Card>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {episodes.map((ep) => (
          <a
            key={ep.videoId}
            href={`https://www.youtube.com/watch?v=${ep.videoId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="group block"
          >
            <Card className="overflow-hidden p-0 transition hover:border-emerald-400/40">
              <div className="relative aspect-video w-full overflow-hidden bg-muted">
                {ep.thumbnail ? (
                  <Image
                    src={ep.thumbnail}
                    alt={ep.title}
                    fill
                    sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
                    className="object-cover transition group-hover:scale-[1.02]"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
                    No thumbnail
                  </div>
                )}
                <span className="absolute bottom-2 right-2 rounded bg-black/80 px-1.5 py-0.5 text-[10px] font-medium text-white tabular-nums">
                  {fmtDuration(ep.durationSeconds)}
                </span>
              </div>
              <div className="p-3">
                <h3 className="line-clamp-2 text-sm font-medium text-foreground">
                  {ep.title}
                </h3>
                {(ep.guest || ep.brand) && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {ep.guest && <span className="text-foreground/80">{ep.guest}</span>}
                    {ep.guest && ep.brand && " · "}
                    {ep.brand && <span>{ep.brand}</span>}
                  </p>
                )}
                <p className="mt-1 text-xs text-muted-foreground tabular-nums">
                  {fmtViews(ep.views)} · {fmtPublishedAgo(ep.publishedAt)}
                </p>
              </div>
            </Card>
          </a>
        ))}
      </div>
      <p className="text-center text-[10px] text-muted-foreground/40 py-4">
        Powered by Graphite
      </p>
    </div>
  );
}
