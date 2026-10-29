// Second Serve data contract. Mirrors the generator's record dicts (generator/sim.py) field-for-field,
// so a generated bundle.json drops in without a mapping layer. Canonical prose: docs/data-model.md.

export const SCENARIOS = ['normal_week', 'game_day', 'finals_week', 'holiday_short_week'] as const
export type ScenarioId = (typeof SCENARIOS)[number]

export const SCENARIO_LABELS: Record<ScenarioId, string> = {
  normal_week: 'Normal week',
  game_day: 'Game day',
  finals_week: 'Finals week',
  holiday_short_week: 'Holiday short week',
}

export type ISODate = string
export type MealPeriod = 'breakfast' | 'brunch' | 'lunch' | 'dinner' | 'late_night'

export interface BundleMeta {
  scenario: ScenarioId | 'fixture'
  description: string
  start_date: ISODate
  end_date: ISODate
  /** The simulated "today": dashboard, inventory and recs read the snapshot for this date. */
  as_of: ISODate
  seed: number
  /** Always null in generator output, to keep same-seed bundles byte-identical. */
  generated_at: string | null
  /** fixture = hand-made by app/scripts/make-fixture.mjs; generator = data/synthetic output. */
  source: 'fixture' | 'generator'
  factors: {
    /** lb of food per meal equivalent, used by Impact. */
    lb_per_meal: number
    /** lb CO2e per lb of food waste avoided. */
    co2e_lb_per_lb: number
  }
}

export interface SourceRef {
  metric?: string
  source_url?: string
  quote?: string | null
  formula?: string
}

export interface Hall {
  id: string
  name: string
  seats: number | null
  covers_per_day: number | null
  covers_source?: SourceRef | null
  hours: Record<string, string>
  feeder_housing?: string | null
  residents: number | null
}

export interface Station {
  id: string
  hall_id: string
  name: string
  cuisine?: string | null
  role?: string | null
}

export type IngredientCategory = 'produce' | 'protein' | 'dairy' | 'grain' | 'bakery' | 'other'

export interface Ingredient {
  ingredient_id: string
  name: string
  category: IngredientCategory | string
  unit: string
  lb_per_unit: number
  shelf_life_days: number
  storage: string
  usd_per_lb: number | null
}

export interface RecipeLine {
  ingredient_id: string
  qty: number
  unit: string
  /** Pounds per batch; present in generator output, absent in the hand-made fixture. */
  qty_lb?: number
}

export interface Recipe {
  recipe_id: string
  name: string
  portions_per_batch: number
  ingredients: RecipeLine[]
}

export interface MenuItem {
  menu_item_id: string
  hall_id: string
  date: ISODate
  meal_period: MealPeriod | string
  station_id: string
  name: string
  recipe_id: string
  serving_lb?: number | null
  take_rate?: number
  station_role?: string
  source_url?: string
}

export interface InventoryLot {
  snapshot_date: ISODate
  snapshot: 'opening' | 'daily' | 'closing'
  lot_id: string
  hall_id: string
  ingredient_id: string
  qty: number
  unit: string
  qty_lb: number
  received_date: ISODate
  expiry_date: ISODate
  origin: 'opening' | 'delivery' | 'emergency' | 'transfer_in' | string
  days_to_expiry: number
}

export interface ProductionRecord {
  hall_id: string
  date: ISODate
  meal_period: MealPeriod | string
  menu_item_id: string
  portions_forecast: number
  portions_prepared: number
  portions_served: number
  portions_wasted?: number
  portions_donated?: number
  portions_repurposed?: number
}

export interface DinerRecord {
  hall_id: string
  date: ISODate
  meal_period: MealPeriod | string
  diners_forecast: number
  diners_actual: number
  multiplier?: number
}

export type WasteKind = 'pre_consumer' | 'post_consumer' | 'expired'

export interface WasteEvent {
  hall_id: string
  date: ISODate
  meal_period: MealPeriod | string
  kind: WasteKind
  reason: string
  ingredient_id: string
  menu_item_id: string
  lot_id: string
  lb: number
  lb_ap?: number
}

export interface Transfer {
  transfer_id: string
  date: ISODate
  from_hall: string
  to_hall: string
  ingredient_id: string
  qty_lb: number
  lot_id: string
  expiry_date: ISODate
  status: 'proposed' | 'completed' | string
  est_lb_saved: number
}

export type RecommendationKind = 'use_first' | 'adjust_prep' | 'buy_less' | 'transfer' | 'recover'

export interface Recommendation {
  id: string
  hall_id: string
  date: ISODate
  kind: RecommendationKind
  /** ingredient_id, menu_item_id or recipe_id depending on kind. */
  target: string
  /** Display name for target, so the card renders without a join. */
  target_name: string
  qty: number
  unit: string
  est_lb_saved: number
  est_usd_saved: number
  rationale: string
  /** Free-form evidence the rec was computed from (lot ids, forecasts, receiving hall). */
  inputs: Record<string, string | number | null>
}

export interface Bundle {
  meta: BundleMeta
  halls: Hall[]
  stations: Station[]
  ingredients: Ingredient[]
  recipes: Recipe[]
  menu_items: MenuItem[]
  inventory: InventoryLot[]
  production: ProductionRecord[]
  diners: DinerRecord[]
  waste: WasteEvent[]
  transfers: Transfer[]
  recommendations: Recommendation[]
}
