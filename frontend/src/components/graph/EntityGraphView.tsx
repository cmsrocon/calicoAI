import { useEffect, useRef, useState } from 'react'
import { useUIStore } from '../../store/uiStore'
import type { EntityGraphLink, EntityGraphNetwork, EntityGraphNode } from '../../types'

type PositionedNode = EntityGraphNode & {
  x: number
  y: number
  radius: number
}

type PositionedLink = EntityGraphLink & {
  strokeWidth: number
}

type GraphLayout = {
  nodes: PositionedNode[]
  links: PositionedLink[]
}

type HoveredLink = {
  link: EntityGraphLink
  left: number
  top: number
}

const WIDTH = 1120
const HEIGHT = 720

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function normalize(value: number, maxValue: number, fallback = 0.5): number {
  if (!Number.isFinite(value) || maxValue <= 0) return fallback
  return clamp(value / maxValue, 0, 1)
}

function nodePalette(type: EntityGraphNode['entity_type']): { fill: string, stroke: string, glow: string } {
  return type === 'vendor'
    ? { fill: '#F97316', stroke: '#FDBA74', glow: 'rgba(249,115,22,0.22)' }
    : { fill: '#38BDF8', stroke: '#BAE6FD', glow: 'rgba(56,189,248,0.22)' }
}

function linkColor(source: PositionedNode, target: PositionedNode): string {
  if (source.entity_type === target.entity_type) {
    return source.entity_type === 'vendor' ? 'rgba(249,115,22,0.55)' : 'rgba(56,189,248,0.5)'
  }
  return 'rgba(245, 158, 11, 0.48)'
}

function computeLayout(graph: EntityGraphNetwork): GraphLayout {
  const maxImportance = Math.max(...graph.nodes.map((node) => node.importance_score), 1)
  const maxStrength = Math.max(...graph.links.map((link) => link.strength_score), 1)
  const centerX = WIDTH / 2
  const centerY = HEIGHT / 2
  const orbitBase = Math.min(WIDTH, HEIGHT) * 0.18

  const nodes = graph.nodes.map((node, index) => {
    const importance = normalize(node.importance_score, maxImportance)
    const radius = 18 + importance * 20
    const ring = Math.floor(index / 6)
    const angle = (index / Math.max(graph.nodes.length, 1)) * Math.PI * 2
    const orbit = orbitBase + ring * 76 + (1 - importance) * 42
    return {
      ...node,
      radius,
      x: centerX + Math.cos(angle) * orbit,
      y: centerY + Math.sin(angle) * orbit,
    }
  })

  if (nodes.length === 1) {
    return {
      nodes: [{ ...nodes[0], x: centerX, y: centerY }],
      links: [],
    }
  }

  const positions = nodes.map((node) => ({ x: node.x, y: node.y, radius: node.radius }))
  const velocities = nodes.map(() => ({ x: 0, y: 0 }))
  const nodeIndex = new Map(nodes.map((node, index) => [node.id, index]))

  for (let iteration = 0; iteration < 220; iteration += 1) {
    for (let i = 0; i < positions.length; i += 1) {
      for (let j = i + 1; j < positions.length; j += 1) {
        const a = positions[i]
        const b = positions[j]
        const dx = b.x - a.x
        const dy = b.y - a.y
        const distance = Math.sqrt(dx * dx + dy * dy) || 1
        const minDistance = a.radius + b.radius + 44
        const force = distance < minDistance
          ? (minDistance - distance) * 0.018
          : 2200 / (distance * distance)
        const fx = (dx / distance) * force
        const fy = (dy / distance) * force

        velocities[i].x -= fx
        velocities[i].y -= fy
        velocities[j].x += fx
        velocities[j].y += fy
      }
    }

    for (const link of graph.links) {
      const sourceIndex = nodeIndex.get(link.source)
      const targetIndex = nodeIndex.get(link.target)
      if (sourceIndex == null || targetIndex == null) continue

      const source = positions[sourceIndex]
      const target = positions[targetIndex]
      const dx = target.x - source.x
      const dy = target.y - source.y
      const distance = Math.sqrt(dx * dx + dy * dy) || 1
      const strength = normalize(link.strength_score, maxStrength)
      const idealDistance = 250 - strength * 120
      const pull = (distance - idealDistance) * (0.0025 + strength * 0.0018)
      const fx = (dx / distance) * pull
      const fy = (dy / distance) * pull

      velocities[sourceIndex].x += fx
      velocities[sourceIndex].y += fy
      velocities[targetIndex].x -= fx
      velocities[targetIndex].y -= fy
    }

    for (let i = 0; i < positions.length; i += 1) {
      const position = positions[i]
      const importance = normalize(nodes[i].importance_score, maxImportance)
      velocities[i].x += (centerX - position.x) * (0.0009 + importance * 0.0004)
      velocities[i].y += (centerY - position.y) * (0.0009 + importance * 0.0004)

      velocities[i].x *= 0.82
      velocities[i].y *= 0.82

      position.x = clamp(position.x + velocities[i].x, position.radius + 24, WIDTH - position.radius - 24)
      position.y = clamp(position.y + velocities[i].y, position.radius + 24, HEIGHT - position.radius - 24)
    }
  }

  return {
    nodes: nodes.map((node, index) => ({
      ...node,
      x: positions[index].x,
      y: positions[index].y,
    })),
    links: graph.links.map((link) => ({
      ...link,
      strokeWidth: 2 + normalize(link.strength_score, maxStrength) * 8,
    })),
  }
}

export default function EntityGraphView({ graph }: { graph: EntityGraphNetwork }) {
  const [layout, setLayout] = useState<GraphLayout>(() => computeLayout(graph))
  const [hoveredLink, setHoveredLink] = useState<HoveredLink | null>(null)
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const { openDetail, setActiveTab } = useUIStore()

  useEffect(() => {
    setLayout(computeLayout(graph))
    setHoveredLink(null)
    setHoveredNodeId(null)
  }, [graph])

  const nodeMap = new Map(layout.nodes.map((node) => [node.id, node]))

  const handleNodeClick = (node: PositionedNode) => {
    if (node.entity_type === 'vendor') {
      setActiveTab('vendors')
      openDetail('vendor', node.entity_id)
      return
    }

    setActiveTab('verticals')
    openDetail('vertical', node.entity_id)
  }

  const handleLinkHover = (link: EntityGraphLink, event: React.MouseEvent<SVGLineElement>) => {
    const bounds = containerRef.current?.getBoundingClientRect()
    if (!bounds) return
    setHoveredLink({
      link,
      left: event.clientX - bounds.left + 16,
      top: event.clientY - bounds.top + 16,
    })
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 text-xs text-stone-500">
        <span className="rounded-full border border-stone-800 bg-stone-900 px-3 py-1.5">
          Click a node to open its detail view
        </span>
        <span className="flex items-center gap-2 rounded-full border border-stone-800 bg-stone-900 px-3 py-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-orange-500" />
          Entities
        </span>
        <span className="flex items-center gap-2 rounded-full border border-stone-800 bg-stone-900 px-3 py-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-sky-400" />
          Themes
        </span>
      </div>

      <div
        ref={containerRef}
        className="relative overflow-hidden rounded-[1.75rem] border border-stone-800 bg-[radial-gradient(circle_at_top,_rgba(249,115,22,0.12),_transparent_26%),radial-gradient(circle_at_bottom_right,_rgba(56,189,248,0.12),_transparent_28%),linear-gradient(180deg,_rgba(28,25,23,0.98),_rgba(12,10,9,0.98))]"
      >
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} className="h-[42rem] w-full">
          <defs>
            <filter id="graphNodeGlow">
              <feGaussianBlur stdDeviation="10" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          <circle cx={WIDTH / 2} cy={HEIGHT / 2} r={220} fill="rgba(255,255,255,0.02)" />
          <circle cx={WIDTH / 2} cy={HEIGHT / 2} r={320} fill="none" stroke="rgba(255,255,255,0.04)" strokeDasharray="4 14" />
          <circle cx={WIDTH / 2} cy={HEIGHT / 2} r={110} fill="none" stroke="rgba(255,255,255,0.03)" strokeDasharray="2 10" />

          {layout.links.map((link) => {
            const source = nodeMap.get(link.source)
            const target = nodeMap.get(link.target)
            if (!source || !target) return null
            const isHovered = hoveredLink?.link.source === link.source && hoveredLink.link.target === link.target
            return (
              <g key={`${link.source}-${link.target}`}>
                <line
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke={linkColor(source, target)}
                  strokeWidth={isHovered ? link.strokeWidth + 1.5 : link.strokeWidth}
                  strokeLinecap="round"
                  opacity={isHovered ? 0.95 : 0.72}
                />
                <line
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke="transparent"
                  strokeWidth={Math.max(link.strokeWidth + 14, 18)}
                  strokeLinecap="round"
                  onMouseEnter={(event) => handleLinkHover(link, event)}
                  onMouseMove={(event) => handleLinkHover(link, event)}
                  onMouseLeave={() => setHoveredLink(null)}
                />
              </g>
            )
          })}

          {layout.nodes.map((node) => {
            const palette = nodePalette(node.entity_type)
            const isHovered = hoveredNodeId === node.id
            const labelY = node.y + node.radius + 18

            return (
              <g
                key={node.id}
                onClick={() => handleNodeClick(node)}
                onMouseEnter={() => setHoveredNodeId(node.id)}
                onMouseLeave={() => setHoveredNodeId((current) => (current === node.id ? null : current))}
                className="cursor-pointer"
              >
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={node.radius + (isHovered ? 10 : 6)}
                  fill={palette.glow}
                  filter="url(#graphNodeGlow)"
                />
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={node.radius}
                  fill={palette.fill}
                  stroke={palette.stroke}
                  strokeWidth={isHovered ? 4 : 2.5}
                />
                <text
                  x={node.x}
                  y={node.y + 4}
                  fill="white"
                  fontSize={node.radius >= 30 ? 12 : 11}
                  fontWeight={700}
                  textAnchor="middle"
                >
                  {node.article_count}
                </text>
                <text
                  x={node.x}
                  y={labelY}
                  fill={isHovered ? '#F5F5F4' : '#D6D3D1'}
                  fontSize={12}
                  fontWeight={isHovered ? 700 : 600}
                  textAnchor="middle"
                >
                  {node.name}
                </text>
              </g>
            )
          })}
        </svg>

        {hoveredLink && (
          <div
            className="pointer-events-none absolute max-w-sm rounded-xl border border-stone-700 bg-stone-950/95 px-4 py-3 shadow-2xl backdrop-blur"
            style={{ left: hoveredLink.left, top: hoveredLink.top }}
          >
            <p className="text-sm font-medium text-stone-100">{hoveredLink.link.description}</p>
            <p className="mt-1 text-xs text-orange-300">
              Strength {hoveredLink.link.strength_score.toFixed(1)} · {hoveredLink.link.article_count} shared articles
            </p>
            {hoveredLink.link.sample_headlines.length > 0 && (
              <div className="mt-2 space-y-1">
                {hoveredLink.link.sample_headlines.slice(0, 2).map((headline) => (
                  <p key={headline} className="text-xs text-stone-400">
                    {headline}
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
