<template>
  <div class="restocking">
    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <!-- Budget card -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Available Budget</h3>
          <span class="budget-readout num">{{ currencySymbol }}{{ budget.toLocaleString() }}</span>
        </div>
        <input
          type="range"
          min="0"
          max="200000"
          step="1000"
          v-model.number="budget"
          class="budget-slider"
        />
        <div class="budget-meta-row">
          <span>Selected total: {{ currencySymbol }}{{ selectedTotal.toLocaleString() }}</span>
          <span>Items selected: {{ selected.size }} of {{ candidates.length }}</span>
        </div>
      </div>

      <!-- Recommendations card -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Recommendations</h3>
        </div>
        <div v-if="candidates.length === 0" class="empty-state">
          All items are above target. No restocking needed.
        </div>
        <div v-else class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th class="col-check"></th>
                <th>SKU</th>
                <th>Item</th>
                <th>Warehouse</th>
                <th>On Hand</th>
                <th>Reorder Point</th>
                <th>Target</th>
                <th>Order Qty</th>
                <th>Unit Cost</th>
                <th>Line Total</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in candidates"
                :key="row.sku"
                :style="{ opacity: isSelected(row.sku) ? 1 : 0.5 }"
              >
                <td class="col-check">
                  <input
                    type="checkbox"
                    :checked="isSelected(row.sku)"
                    @change="toggle(row.sku)"
                  />
                </td>
                <td><strong>{{ row.sku }}</strong></td>
                <td>{{ row.name }}</td>
                <td>{{ row.warehouse }}</td>
                <td class="num">{{ row.on_hand }}</td>
                <td class="num">{{ row.reorder_point }}</td>
                <td class="num">{{ row.target }}</td>
                <td class="num"><strong>{{ row.orderQty }}</strong></td>
                <td class="num">{{ currencySymbol }}{{ row.unit_cost.toLocaleString() }}</td>
                <td class="num"><strong>{{ currencySymbol }}{{ row.lineTotal.toLocaleString() }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Footer action row -->
      <div class="card action-row">
        <span :class="['budget-status', { 'over-budget': selectedTotal > budget }]">
          Selected total {{ currencySymbol }}{{ selectedTotal.toLocaleString() }} / Budget {{ currencySymbol }}{{ budget.toLocaleString() }}
        </span>
        <div class="action-right">
          <button
            class="btn btn-primary"
            :disabled="selected.size === 0 || selectedTotal > budget || submitting || candidates.length === 0"
            @click="placeOrder"
          >
            {{ submitting ? 'Submitting...' : 'Place Order' }}
          </button>
          <div v-if="submitError" class="submit-error">{{ submitError }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency } = useI18n()
    const router = useRouter()

    const loading = ref(true)
    const error = ref(null)
    const submitting = ref(false)
    const submitError = ref(null)

    const forecasts = ref([])
    const inventory = ref([])
    const budget = ref(50000)
    const selected = ref(new Set())

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const candidates = computed(() => {
      const rows = []

      for (const forecast of forecasts.value) {
        const inv = inventory.value.find(i => i.sku === forecast.item_sku)
        if (!inv) continue

        // why: target is set to 1.5× the reorder point to provide a safety buffer above
        // the minimum threshold, topping the item up rather than just barely clearing it.
        const target = Math.ceil(inv.reorder_point * 1.5)
        const orderQty = Math.max(0, target - inv.quantity_on_hand)
        if (orderQty === 0) continue

        const lineTotal = orderQty * inv.unit_cost
        const gap = forecast.forecasted_demand - forecast.current_demand

        rows.push({
          sku: inv.sku,
          name: inv.name,
          warehouse: inv.warehouse,
          category: inv.category,
          on_hand: inv.quantity_on_hand,
          reorder_point: inv.reorder_point,
          target,
          orderQty,
          unit_cost: inv.unit_cost,
          lineTotal,
          trend: forecast.trend,
          gap
        })
      }

      // Sort increasing trend first, then by gap descending
      rows.sort((a, b) => {
        if (a.trend === 'increasing' && b.trend !== 'increasing') return -1
        if (b.trend === 'increasing' && a.trend !== 'increasing') return 1
        return b.gap - a.gap
      })

      return rows
    })

    const autoSelect = () => {
      // why: we walk candidates in priority order (increasing trend, highest gap first) so
      // that the greedy budget fill naturally chooses the highest-urgency items first.
      const newSet = new Set()
      let running = 0
      for (const row of candidates.value) {
        if (running + row.lineTotal <= budget.value) {
          newSet.add(row.sku)
          running += row.lineTotal
        }
      }
      selected.value = newSet
    }

    const isSelected = (sku) => selected.value.has(sku)

    const toggle = (sku) => {
      const next = new Set(selected.value)
      if (next.has(sku)) {
        next.delete(sku)
      } else {
        next.add(sku)
      }
      selected.value = next
    }

    const selectedRows = computed(() => {
      return candidates.value.filter(r => isSelected(r.sku))
    })

    const selectedTotal = computed(() => {
      return selectedRows.value.reduce((sum, r) => sum + r.lineTotal, 0)
    })

    const loadData = async () => {
      loading.value = true
      error.value = null
      try {
        const [forecastData, inventoryData] = await Promise.all([
          api.getDemandForecasts(),
          api.getInventory()
        ])
        forecasts.value = forecastData
        inventory.value = inventoryData
        autoSelect()
      } catch (err) {
        error.value = 'Failed to load restocking data: ' + err.message
      } finally {
        loading.value = false
      }
    }

    watch(budget, () => {
      autoSelect()
    })

    const placeOrder = async () => {
      submitting.value = true
      submitError.value = null
      try {
        const items = selectedRows.value.map(r => ({
          sku: r.sku,
          name: r.name,
          quantity: r.orderQty,
          unit_cost: r.unit_cost,
          warehouse: r.warehouse,
          category: r.category
        }))
        await api.submitRestockingOrder({ items, budget: budget.value })
        router.push('/orders')
      } catch (err) {
        submitError.value = 'Failed to submit order. Please try again.'
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadData)

    return {
      t,
      loading,
      error,
      submitting,
      submitError,
      budget,
      selected,
      candidates,
      currencySymbol,
      selectedTotal,
      isSelected,
      toggle,
      placeOrder
    }
  }
}
</script>

<style scoped>
.restocking {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.budget-readout {
  font-size: var(--text-2xl);
  font-weight: var(--weight-bold);
  color: var(--color-text);
}

/* ---- Budget slider ---- */
.budget-slider {
  width: 100%;
  margin: var(--space-3) 0 var(--space-2);
  cursor: pointer;
  -webkit-appearance: none;
  appearance: none;
  height: 6px;
  border-radius: var(--radius-pill);
  background: var(--color-border-strong);
  outline: none;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-accent);
  border: 2px solid var(--color-surface);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: background var(--duration-fast) var(--ease-out);
}

.budget-slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-accent);
  border: 2px solid var(--color-surface);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
}

.budget-slider:focus-visible {
  box-shadow: var(--focus-ring);
  border-radius: var(--radius-pill);
}

/* Filled track (webkit only — Firefox uses accent-color) */
.budget-slider::-webkit-slider-runnable-track {
  height: 6px;
  border-radius: var(--radius-pill);
}

.budget-meta-row {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin-top: var(--space-1);
}

.col-check {
  width: 36px;
}

.empty-state {
  padding: var(--space-8);
  text-align: center;
  color: var(--color-text-muted);
  font-size: var(--text-base);
}

.action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.budget-status {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.budget-status.over-budget {
  color: var(--color-danger);
  font-weight: var(--weight-semibold);
}

.action-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-2);
}

.submit-error {
  font-size: var(--text-sm);
  color: var(--color-danger);
}
</style>
