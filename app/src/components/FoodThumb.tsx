import { Utensils } from 'lucide-react'
import { foodPhoto } from '@/data/food-images'
import { cn } from '@/lib/utils'

export function FoodThumb({ name, id, size = 38 }: { name: string; id?: string; size?: number }) {
  const src = foodPhoto(id, name)
  return (
    <span
      className={cn(
        'grid flex-none place-items-center overflow-hidden rounded-full bg-[#f1efe8] text-muted-foreground',
      )}
      style={{ width: size, height: size }}
    >
      {src ? (
        <img src={src} alt="" className="size-full object-cover" loading="lazy" />
      ) : (
        <Utensils className="size-4" aria-hidden="true" />
      )}
    </span>
  )
}
