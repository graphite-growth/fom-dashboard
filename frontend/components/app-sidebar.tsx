"use client"

import * as React from "react"

import {
  BarChart3,
  Calendar,
  CalendarDays,
  CalendarRange,
  ChevronRight,
  Users,
} from "lucide-react"

import { GraphiteLogo } from "@/components/ui/graphite-logo"
import { NavUser } from "@/components/nav-user"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarRail,
} from "@/components/ui/sidebar"

export type DashboardSection =
  | "views-daily"
  | "views-weekly"
  | "views-monthly"
  | "subscribers-overview"

type AppSidebarProps = React.ComponentProps<typeof Sidebar> & {
  user: { name: string; email: string; image: string }
  active: DashboardSection
  onSectionChange: (section: DashboardSection) => void
}

interface NavGroup {
  label: string
  icon: React.ElementType
  items: { id: DashboardSection; label: string; icon: React.ElementType }[]
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Views",
    icon: BarChart3,
    items: [
      { id: "views-daily", label: "Daily Performance", icon: Calendar },
      { id: "views-weekly", label: "Weekly Performance", icon: CalendarDays },
      { id: "views-monthly", label: "Monthly Performance", icon: CalendarRange },
    ],
  },
  {
    label: "Subscribers",
    icon: Users,
    items: [{ id: "subscribers-overview", label: "Overview", icon: Calendar }],
  },
]

export function AppSidebar({ user, active, onSectionChange, ...props }: AppSidebarProps) {
  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <a href="/app">
                <div className="bg-sidebar-primary text-sidebar-primary-foreground flex aspect-square size-8 items-center justify-center rounded-lg">
                  <GraphiteLogo className="size-4" />
                </div>
                <div className="grid flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-medium">{"FOM Dashboard"}</span>
                </div>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_GROUPS.map((group) => {
                const groupActive = group.items.some((it) => it.id === active)
                const Icon = group.icon
                return (
                  <Collapsible
                    key={group.label}
                    defaultOpen={groupActive}
                    className="group/collapsible"
                    asChild
                  >
                    <SidebarMenuItem>
                      <CollapsibleTrigger asChild>
                        <SidebarMenuButton tooltip={group.label}>
                          <Icon />
                          <span>{group.label}</span>
                          <ChevronRight className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                        </SidebarMenuButton>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <SidebarMenuSub>
                          {group.items.map(({ id, label, icon: SubIcon }) => (
                            <SidebarMenuSubItem key={id}>
                              <SidebarMenuSubButton
                                isActive={active === id}
                                onClick={() => onSectionChange(id)}
                                className="cursor-pointer"
                              >
                                <SubIcon />
                                <span>{label}</span>
                              </SidebarMenuSubButton>
                            </SidebarMenuSubItem>
                          ))}
                        </SidebarMenuSub>
                      </CollapsibleContent>
                    </SidebarMenuItem>
                  </Collapsible>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={user} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
