"use client"

import { useEffect, useRef, useState } from "react"
import { searchStations, StationResult } from "@/lib/api"
import styles from "./StationSearch.module.css"

interface Props {
  selected: StationResult | null
  onSelect: (station: StationResult | null) => void
}

export default function StationSearch({ selected, onSelect }: Props) {
  const [input, setInput] = useState("")
  const [results, setResults] = useState<StationResult[]>([])
  const [open, setOpen] = useState(false)
  const [activeIdx, setActiveIdx] = useState(-1)
  const [loading, setLoading] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!input.trim()) {
      setResults([])
      setOpen(false)
      return
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true)
      try {
        const data = await searchStations(input.trim())
        setResults(data.slice(0, 8))
        setOpen(data.length > 0)
        setActiveIdx(-1)
      } catch {
        setResults([])
        setOpen(false)
      } finally {
        setLoading(false)
      }
    }, 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [input])

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open) return
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setActiveIdx((i) => Math.min(i + 1, results.length - 1))
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setActiveIdx((i) => Math.max(i - 1, -1))
    } else if (e.key === "Enter") {
      e.preventDefault()
      if (activeIdx >= 0 && results[activeIdx]) {
        pick(results[activeIdx])
      }
    } else if (e.key === "Escape") {
      setOpen(false)
    }
  }

  const pick = (station: StationResult) => {
    onSelect(station)
    setInput("")
    setOpen(false)
    setResults([])
  }

  const clear = () => {
    onSelect(null)
    setInput("")
    inputRef.current?.focus()
  }

  if (selected) {
    return (
      <div className={styles.selectedBadge}>
        <span className={styles.subwayIcon}>🚇</span>
        <span className={styles.selectedName}>{selected.name}역</span>
        <button type="button" className={styles.clearBtn} onClick={clear} aria-label="역 선택 해제">
          ✕
        </button>
      </div>
    )
  }

  return (
    <div className={styles.container} ref={containerRef}>
      <div className={styles.inputWrapper}>
        <span className={styles.inputIcon}>🚇</span>
        <input
          ref={inputRef}
          type="text"
          className={styles.input}
          placeholder="지하철역 검색... (예: 홍대입구)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => results.length > 0 && setOpen(true)}
          autoComplete="off"
          aria-label="지하철역 검색"
          aria-expanded={open}
          aria-autocomplete="list"
        />
        {loading && <span className={styles.loadingDot} />}
      </div>

      {open && results.length > 0 && (
        <ul className={styles.dropdown} role="listbox">
          {results.map((s, i) => (
            <li
              key={s.station_id}
              role="option"
              aria-selected={i === activeIdx}
              className={`${styles.item} ${i === activeIdx ? styles.itemActive : ""}`}
              onMouseEnter={() => setActiveIdx(i)}
              onMouseDown={(e) => { e.preventDefault(); pick(s) }}
            >
              <span className={styles.itemIcon}>🚇</span>
              <span className={styles.itemName}>{s.name}</span>
              <span className={styles.itemSuffix}>역</span>
            </li>
          ))}
        </ul>
      )}

      {open && results.length === 0 && !loading && input.trim() && (
        <div className={styles.empty}>검색 결과가 없어요</div>
      )}
    </div>
  )
}
