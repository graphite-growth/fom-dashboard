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
}
