export interface AdGroup {
  name: string;
  views: number;
  cost: number;
  cpv: number;
  impressions: number;
  viewRate: number;
  q25: number;
  q50: number;
  q75: number;
  q100: number;
}

export interface Video {
  name: string;
  views: number;
  cost: number;
  cpv: number;
  impressions: number;
  viewRate: number;
  publicViews: number;
  likes: number;
  comments: number;
  q25: number;
  q50: number;
  q75: number;
  q100: number;
  adGroups: AdGroup[];
}

export interface DailyData {
  date: string;
  views: number;
  cost: number;
}

export interface SubscriberSnapshot {
  date: string;
  subscribers: number;
}

export interface DemographicRow {
  label: string;
  views: number;
  cost: number;
  impressions: number;
  pctOfViews: number;
}

export interface Demographics {
  age: DemographicRow[];
  gender: DemographicRow[];
  device: DemographicRow[];
  geo: DemographicRow[];
}

export interface SubscribersDailyPoint {
  date: string;
  newSubs: number;
  cost: number;
  impressions: number;
}

export interface SubscribersCampaign {
  campaignNames: string[];
  campaignStart: string;
  subsGained: number;
  cost: number;
  impressions: number;
  costPerSub: number;
  convRate: number;
  daily: SubscribersDailyPoint[];
}

export type PhaseStatus = "closed" | "in-progress";

export interface Phase {
  id: string;
  label: string;
  start: string;
  end: string;
  budget: number;
  status: PhaseStatus;
}

export interface PhaseScopedData {
  phase: Phase;
  videos: Video[];
  daily: DailyData[];
  demographics: Demographics;
  totalPaidViews: number;
  totalSpend: number;
  totalImpressions: number;
  totalPublicViews: number;
  avgCPV: number;
  projectedPaidViews: number;
  lastUpdated: string;
}

export interface Episode {
  videoId: string;
  title: string;
  publishedAt: string;
  durationSeconds: number;
  thumbnail: string;
  views: number;
  likes: number;
  comments: number;
  brand: string;
  guest: string;
}

export interface DashboardData {
  budget: number;
  flightStart: string;
  flightEnd: string;
  lastUpdated: string;
  organicMultiplier: number;
  videos: Video[];
  daily: DailyData[];
  subscribers?: number;
  totalChannelViews?: number;
  projectedPaidViews?: number;
  projectedPublicViews?: number;
  subscriberHistory?: SubscriberSnapshot[];
  demographics?: Demographics;
  subscribersCampaign?: SubscribersCampaign;
  phases?: Phase[];
  defaultPhaseId?: string;
  episodes?: Episode[];
}
