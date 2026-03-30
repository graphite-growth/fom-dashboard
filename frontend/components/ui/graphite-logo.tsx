// components/app-sidebar.tsx

import Image from "next/image"

export function GraphiteLogo({ className }: { className?: string }) {
  return (
    <div className={className}>
      <Image
        src="/graphitehq_logo.png"
        alt="G"
        width={32}
        height={32}
        className="object-contain"
      />
    </div>
  )
}
