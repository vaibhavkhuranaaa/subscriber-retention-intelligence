import { useEffect, useRef } from 'react'
import * as echarts from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { SVGRenderer } from 'echarts/renderers'
import type { EChartsCoreOption } from 'echarts/core'

echarts.use([BarChart, LineChart, GridComponent, TooltipComponent, SVGRenderer])

export default function Chart({ option, label }: { option: EChartsCoreOption; label: string }) {
  const target = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!target.current) return
    const chart = echarts.init(target.current, undefined, { renderer: 'svg' })
    chart.setOption(option)
    const resize = new ResizeObserver(() => chart.resize())
    resize.observe(target.current)
    return () => {
      resize.disconnect()
      chart.dispose()
    }
  }, [option])
  return <div className="chart" ref={target} role="img" aria-label={label} />
}
