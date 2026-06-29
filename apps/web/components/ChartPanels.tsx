"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import type { FactRow } from "@/lib/api";
import { formatAxisValue, formatValue } from "@/lib/format";

type ChartDatum = {
  label?: string;
  provider?: string;
  unit?: string;
  value: number;
  year?: number;
  [key: string]: string | number | undefined;
};

export function RankingBarChart({ rows }: { rows: FactRow[] }) {
  const data = rows.slice(0, 8).map((row) => ({
    provider: row.provider_name?.replace("The University of ", "U. ") ?? row.provider_id,
    unit: row.unit,
    value: row.value
  }));
  const axisUnit = singleUnit(rows);
  if (!data.length) return <EmptyChart />;
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <BarChart data={data} layout="vertical" margin={{ left: 20, right: 20, top: 8, bottom: 8 }}>
          <CartesianGrid stroke="#e7edf3" horizontal={false} />
          <XAxis tickFormatter={(value) => formatAxisValue(Number(value), axisUnit)} type="number" tick={{ fontSize: 11 }} />
          <YAxis dataKey="provider" type="category" width={130} tick={{ fontSize: 11 }} />
          <Tooltip formatter={formatTooltipValue} />
          <Bar dataKey="value" fill="#147f82" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function TrendLineChart({ rows }: { rows: FactRow[] }) {
  const data = rows.map((row) => ({
    unit: row.unit,
    year: row.reporting_year,
    value: row.value
  }));
  const axisUnit = singleUnit(rows);
  if (!data.length) return <EmptyChart />;
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ left: 8, right: 20, top: 12, bottom: 8 }}>
          <CartesianGrid stroke="#e7edf3" />
          <XAxis dataKey="year" tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(value) => formatAxisValue(Number(value), axisUnit)} tick={{ fontSize: 11 }} />
          <Tooltip formatter={formatTooltipValue} />
          <Line dataKey="value" stroke="#147f82" strokeWidth={2} dot={{ r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function MultiProviderTrendChart({ rows }: { rows: FactRow[] }) {
  const providerMap = new Map<string, string>();
  const yearMap = new Map<number, ChartDatum>();

  for (const row of rows) {
    const key = row.provider_id ?? row.provider_name;
    if (!key) continue;
    providerMap.set(key, shortProviderName(row.provider_name ?? key));

    const datum = yearMap.get(row.reporting_year) ?? {
      year: row.reporting_year,
      unit: row.unit,
      value: row.value
    };
    datum[key] = row.value;
    yearMap.set(row.reporting_year, datum);
  }

  const data = Array.from(yearMap.values()).sort((a, b) => Number(a.year) - Number(b.year));
  const providers = Array.from(providerMap.entries()).map(([key, label], index) => ({
    key,
    label,
    color: chartColors[index % chartColors.length]
  }));
  const axisUnit = singleUnit(rows);

  if (!data.length || !providers.length) return <EmptyChart />;

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ left: 8, right: 24, top: 12, bottom: 8 }}>
          <CartesianGrid stroke="#e7edf3" />
          <XAxis dataKey="year" allowDecimals={false} tick={{ fontSize: 11 }} />
          <YAxis tickFormatter={(value) => formatAxisValue(Number(value), axisUnit)} tick={{ fontSize: 11 }} />
          <Tooltip formatter={(value, name) => [formatValue(Number(value), axisUnit), name]} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {providers.map((provider) => (
            <Line
              dataKey={provider.key}
              dot={{ r: 3 }}
              key={provider.key}
              name={provider.label}
              stroke={provider.color}
              strokeWidth={2}
              type="monotone"
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function CompareBarChart({ rows }: { rows: FactRow[] }) {
  const data = rows.map((row) => ({
    label: shortProviderName(row.provider_name ?? row.provider_id ?? ""),
    unit: row.unit,
    value: row.value
  }));
  const axisUnit = singleUnit(rows);
  if (!data.length) return <EmptyChart />;
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ left: 8, right: 20, top: 12, bottom: 32 }}>
          <CartesianGrid stroke="#e7edf3" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={56} />
          <YAxis tickFormatter={(value) => formatAxisValue(Number(value), axisUnit)} tick={{ fontSize: 11 }} />
          <Tooltip formatter={formatTooltipValue} />
          <Bar dataKey="value" fill="#b7791f" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function formatTooltipValue(value: unknown, _name: unknown, item: { payload?: ChartDatum }) {
  const numericValue = Number(value);
  return [formatValue(Number.isFinite(numericValue) ? numericValue : null, item.payload?.unit), "Value"];
}

function singleUnit(rows: FactRow[]) {
  const units = new Set(rows.map((row) => row.unit));
  return units.size === 1 ? rows[0]?.unit : undefined;
}

function shortProviderName(name: string) {
  return name.replace("The University of ", "U. ").replace("University of ", "U. ");
}

const chartColors = ["#147f82", "#b7791f", "#4f46e5", "#be123c", "#15803d"];

function EmptyChart() {
  return (
    <div className="flex h-72 items-center justify-center rounded-md border border-dashed border-line bg-slate-50 text-sm text-muted">
      No data for the selected metric.
    </div>
  );
}
