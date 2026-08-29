'use client';

import { useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Braces,
  Building2,
  ChevronRight,
  Download,
  FileQuestion,
  Gauge,
  Landmark,
  Search,
  ShieldCheck,
  Sparkles,
  type LucideIcon,
} from 'lucide-react';
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Progress, ProgressLabel, ProgressValue } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import aiVisibilityRun from './data/ai-visibility-run.json';

type Category = { name: string; score: number; affected: number };
type Family = {
  id: string;
  number: string;
  name: string;
  owners: string;
  question: string;
  navMetric: string;
  findings: number;
  icon: LucideIcon;
  score?: number;
  pass?: number;
  fail?: number;
  partial?: number;
  manual?: number;
  categories: Category[];
};

const families: Family[] = [
  {
    id: 'ai', number: '01', name: 'AI Visibility', icon: Sparkles, navMetric: '1 of 3 models', findings: 4,
    owners: 'IR · Communications · Corporate Affairs · Marketing',
    question: 'How visible is povarchik.com in AI answers, and which sources are shaping those answers?',
    categories: [
      { name: 'GEO readiness', score: 76, affected: 0 },
      { name: 'AEO readiness', score: 81, affected: 0 },
      { name: 'Combined readiness', score: 78, affected: 0 },
      { name: 'Observed AI visibility', score: 0, affected: 16 },
    ],
  },
  {
    id: 'identity', number: '02', name: 'Identity & Authority', icon: Landmark, navMetric: '53 readiness', findings: 80,
    owners: 'IR · Communications · Brand',
    question: 'Can machines and external audiences clearly establish who povarchik.com represents and why it is authoritative?',
    score: 53, pass: 93, fail: 80, partial: 19, manual: 32,
    categories: [
      { name: 'Entity clarity', score: 74, affected: 36 },
      { name: 'Authority & trust', score: 25, affected: 63 },
    ],
  },
  {
    id: 'evidence', number: '03', name: 'Evidence & Trust', icon: ShieldCheck, navMetric: '16 readiness', findings: 63,
    owners: 'IR · Communications · Editorial · Legal',
    question: 'Does the published information carry evidence, attribution, and accountability?',
    score: 16, pass: 12, fail: 63, partial: 1, manual: 26,
    categories: [{ name: 'Evidence & citations', score: 16, affected: 64 }],
  },
  {
    id: 'content', number: '04', name: 'Content & Answer Readiness', icon: FileQuestion, navMetric: '62 readiness', findings: 146,
    owners: 'Communications · Content · Editorial',
    question: 'Can people, search engines, and answer systems understand and reuse the site’s information?',
    score: 62, pass: 261, fail: 146, partial: 67, manual: 80,
    categories: [
      { name: 'Question & intent alignment', score: 32, affected: 74 },
      { name: 'Answer extractability', score: 68, affected: 53 },
      { name: 'Content depth & originality', score: 61, affected: 54 },
      { name: 'Clarity & readability', score: 80, affected: 32 },
    ],
  },
  {
    id: 'machine', number: '05', name: 'Machine Readability', icon: Braces, navMetric: '84 readiness', findings: 66,
    owners: 'SEO · Content · Web',
    question: 'Is the site’s information expressed so search and answer systems can identify, interpret, and use it?',
    score: 84, pass: 360, fail: 66, partial: 4, manual: 16,
    categories: [
      { name: 'Search & answer eligibility', score: 78, affected: 32 },
      { name: 'Structured data', score: 88, affected: 15 },
      { name: 'Semantic structure', score: 87, affected: 23 },
    ],
  },
  {
    id: 'seo', number: '06', name: 'SEO Audit', icon: Search, navMetric: '710 impressions', findings: 16,
    owners: 'SEO · Growth · Marketing',
    question: 'Where is search demand being won, lost, or served by the wrong page?',
    categories: [],
  },
  {
    id: 'onsite', number: '07', name: 'Onsite Audit', icon: Activity, navMetric: '17 crawled', findings: 24,
    owners: 'SEO · Web · Engineering',
    question: 'Which technical controls prevent important information from being discovered and used?',
    categories: [],
  },
];

const pageScores = [
  { page: '/', geo: 80, aeo: 80, combined: 80 },
  { page: '/ai-language-governance', geo: 75, aeo: 83, combined: 79 },
  { page: '/ai-system-audit', geo: 75, aeo: 83, combined: 79 },
  { page: '/ai-system-troubleshooting', geo: 75, aeo: 83, combined: 79 },
  { page: '/ai-systems-governance', geo: 76, aeo: 80, combined: 78 },
  { page: '/before-the-code-exists-a-decision-is-already-made-field-notes', geo: 77, aeo: 80, combined: 79 },
  { page: '/blog', geo: 68, aeo: 68, combined: 68 },
  { page: '/cognitive-leverage-operators', geo: 75, aeo: 87, combined: 81 },
  { page: '/engage', geo: 81, aeo: 81, combined: 81 },
  { page: '/honesty-contract', geo: 77, aeo: 84, combined: 81 },
  { page: '/jarvis-the-peacock', geo: 78, aeo: 83, combined: 80 },
  { page: '/system-initialization-specification-reading', geo: 74, aeo: 81, combined: 77 },
  { page: '/the-crossover-ai-iteration-density-theory', geo: 75, aeo: 87, combined: 80 },
  { page: '/when-ai-governance-becomes-real', geo: 78, aeo: 82, combined: 80 },
  { page: '/work', geo: 67, aeo: 68, combined: 68 },
  { page: '/you-decided', geo: 78, aeo: 86, combined: 82 },
];

const scoreConfig = {
  geo: { label: 'GEO', color: 'var(--chart-cited)' },
  aeo: { label: 'AEO', color: 'var(--chart-mentioned)' },
} satisfies ChartConfig;

const searchRows = [
  { query: 'what is povarchik.com domain used for', page: '/cognitive-leverage-operators/', impressions: 144, best: 2, latest: 7, status: 'active 7d' },
  { query: 'povarchik.com', page: '/engage/', impressions: 122, best: 2, latest: 6, status: 'active 7d' },
  { query: 'povarchik.com', page: '/', impressions: 121, best: 1, latest: 2, status: 'active 7d' },
  { query: 'what is povarchik.com domain used for', page: '/the-crossover-ai-iteration-density-theory/', impressions: 89, best: 2, latest: 6, status: 'active 7d' },
  { query: 'povarchik.com', page: '/ai-language-governance/', impressions: 46, best: 2, latest: 27, status: 'active 7d' },
  { query: 'what is povarchik.com domain used for', page: '/', impressions: 36, best: 1.8, latest: 4, status: 'active 7d' },
  { query: 'cognitive leverage', page: '/cognitive-leverage-operators/', impressions: 35, best: 6, latest: 9, status: 'active 7d' },
  { query: 'povarchik.com', page: '/you-decided/', impressions: 21, best: 2, latest: 7, status: 'active 30d' },
];

const technicalIssues = [
  { severity: 'High', issue: 'Missing title tag', page: '/system-initialization-specification-code/system-initializ…' },
  { severity: 'Medium', issue: 'Missing H1', page: '/system-initialization-specification-code/system-initializ…' },
  { severity: 'Medium', issue: 'Missing canonical URL', page: '/system-initialization-specification-code/system-initializ…' },
  { severity: 'Medium', issue: 'Missing meta description', page: '/blog/' },
  { severity: 'Medium', issue: 'Missing meta description', page: '/work/' },
  { severity: 'Medium', issue: 'Missing viewport meta tag', page: '/system-initialization-specification-code/system-initializ…' },
  { severity: 'Low', issue: 'Long title tag', page: '9 pages' },
  { severity: 'Low', issue: 'Low visible word count', page: '3 pages' },
  { severity: 'Low', issue: 'Multiple H1 headings', page: '3 pages' },
  { severity: 'Low', issue: 'No JSON-LD schema detected', page: '1 page' },
];

const priorityFindings = [
  {
    title: 'Observed AI visibility is not measured',
    detail: 'All 16 audited pages require a separate fixed-question visibility study with captured answers and citations.',
    breadth: '16 pages',
  },
  {
    title: 'Answer completeness needs human review',
    detail: 'Structural extraction cannot establish correctness, qualifications, or missing decision-critical facts.',
    breadth: '16 pages',
  },
  {
    title: 'Claims require factual verification',
    detail: 'Material claims need review against primary evidence with the review recorded.',
    breadth: '16 pages',
  },
  {
    title: 'Originality and added value need review',
    detail: 'The report cannot confirm originality from a single-page structural audit.',
    breadth: '16 pages',
  },
];

function ScoreCard({
  label,
  value,
  context,
  direction,
}: {
  label: string;
  value: string;
  context: string;
  direction?: 'up' | 'down';
}) {
  return (
    <Card size="sm" className="min-w-0">
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-2xl font-semibold tracking-tight">{value}</CardTitle>
        {direction ? (
          <CardAction>
            {direction === 'up' ? (
              <ArrowUpRight className="size-4 text-[var(--success)]" />
            ) : (
              <ArrowDownRight className="size-4 text-[var(--danger)]" />
            )}
          </CardAction>
        ) : null}
      </CardHeader>
      <CardContent className="text-xs text-muted-foreground">{context}</CardContent>
    </Card>
  );
}

function Sidebar({
  familyId,
  onChange,
}: {
  familyId: string;
  onChange: (id: string) => void;
}) {
  return (
    <aside className="border-r border-sidebar-border bg-sidebar px-3 py-5 max-lg:hidden">
      <p className="mb-3 px-2 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Report families
      </p>
      <nav aria-label="Report families" className="space-y-1">
        {families.map((family) => {
          const Icon = family.icon;
          const active = family.id === familyId;
          return (
            <button
              key={family.id}
              type="button"
              onClick={() => onChange(family.id)}
              aria-current={active ? 'page' : undefined}
              className={`group flex w-full items-center gap-3 rounded-lg px-2.5 py-2.5 text-left transition-colors ${
                active
                  ? 'bg-sidebar-primary text-sidebar-primary-foreground'
                  : 'text-sidebar-foreground hover:bg-sidebar-accent'
              }`}
            >
              <Icon className="size-4 shrink-0" aria-hidden="true" />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">{family.name}</span>
                <span className={`block text-[11px] ${active ? 'opacity-70' : 'text-muted-foreground'}`}>
                  {family.navMetric} · {family.findings} findings
                </span>
              </span>
              <ChevronRight className={`size-3.5 ${active ? 'opacity-100' : 'opacity-0 group-hover:opacity-60'}`} />
            </button>
          );
        })}
      </nav>
      <div className="mt-6 border-t border-sidebar-border px-2 pt-5">
        <p className="text-xs font-medium text-sidebar-foreground">Audit run #14 · partial</p>
        <p className="mt-1 text-[11px] text-muted-foreground">16 audited pages · 17 crawled</p>
      </div>
    </aside>
  );
}

function ReadinessChart({ band }: { band: string }) {
  const data = pageScores.filter((item) => {
    if (band === 'low') return item.combined < 75;
    if (band === 'mid') return item.combined >= 75 && item.combined < 80;
    if (band === 'high') return item.combined >= 80;
    return true;
  });
  return (
    <ChartContainer config={scoreConfig} className="h-[470px] w-full aspect-auto" initialDimension={{ width: 720, height: 470 }}>
      <BarChart accessibilityLayer data={data} layout="vertical" margin={{ left: 8, right: 18 }} barCategoryGap={5}>
        <CartesianGrid horizontal={false} />
        <YAxis dataKey="page" type="category" tickLine={false} axisLine={false} width={184} tickFormatter={(value) => value.length > 25 ? `${value.slice(0, 23)}…` : value} />
        <XAxis type="number" domain={[0, 100]} tickLine={false} axisLine={false} />
        <ChartTooltip cursor={false} content={<ChartTooltipContent />} />
        <Bar dataKey="geo" fill="var(--color-geo)" radius={[0, 4, 4, 0]} />
        <Bar dataKey="aeo" fill="var(--color-aeo)" radius={[0, 4, 4, 0]} />
      </BarChart>
    </ChartContainer>
  );
}

function PageScoreTable({
  selected,
  onSelect,
  rows = pageScores,
}: {
  selected: string;
  onSelect: (page: string) => void;
  rows?: typeof pageScores;
}) {
  return (
    <div className="overflow-x-auto">
      <div className="min-w-[620px]">
        <div className="grid grid-cols-[minmax(300px,1fr)_72px_72px_92px] gap-2 border-b px-3 pb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          <span>Audited page</span><span className="text-right">GEO</span><span className="text-right">AEO</span><span className="text-right">Combined</span>
        </div>
        {rows.map((item) => (
          <button
            key={item.page}
            type="button"
            onClick={() => onSelect(item.page)}
            aria-pressed={selected === item.page}
            className="grid w-full grid-cols-[minmax(300px,1fr)_72px_72px_92px] items-center gap-2 border-b px-3 py-2.5 text-left text-sm transition-colors hover:bg-muted/60 aria-pressed:bg-accent"
          >
            <span className="truncate font-medium">{item.page}</span>
            <span className="text-right font-mono">{item.geo}</span>
            <span className="text-right font-mono">{item.aeo}</span>
            <span className="text-right"><Badge variant={item.combined < 75 ? 'destructive' : item.combined >= 80 ? 'secondary' : 'outline'}>{item.combined}</Badge></span>
          </button>
        ))}
      </div>
    </div>
  );
}

function PageEvidence({ page }: { page: string }) {
  const score = pageScores.find((item) => item.page === page) ?? pageScores[0];
  return (
    <Card className="h-fit">
      <CardHeader>
        <CardDescription>Selected page</CardDescription>
        <CardTitle className="break-all">{score.page}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid grid-cols-3 gap-2">
          {[['GEO', score.geo], ['AEO', score.aeo], ['Combined', score.combined]].map(([label, value]) => (
            <div key={label} className="rounded-lg bg-muted/60 p-3 text-center"><strong className="block font-mono text-xl">{value}</strong><span className="text-xs text-muted-foreground">{label}</span></div>
          ))}
        </div>
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">Critical manual reviews</p>
          <ul className="space-y-2 text-sm">
            {['Answer completeness and accuracy', 'Claims are factually verified', 'Observed AI visibility is measured separately', 'Originality and added value', 'Primary user intent is satisfied'].map((item) => (
              <li key={item} className="flex gap-2"><AlertTriangle className="mt-0.5 size-4 shrink-0 text-[var(--warning)]" /><span>{item}</span></li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}

function AiStudyView({
  selected,
  onSelect,
}: {
  selected: string;
  onSelect: (questionId: string) => void;
}) {
  const modelRun = aiVisibilityRun.runs[0];
  const result = modelRun.results.find((item) => item.question_id === selected) ?? modelRun.results[0];

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(300px,.75fr)_minmax(0,1.25fr)]">
      <Card className="h-fit">
        <CardHeader>
          <CardDescription>{modelRun.provider} · {modelRun.model}</CardDescription>
          <CardTitle>Four-question visibility run</CardTitle>
          <CardAction><Badge variant="secondary">Live search {modelRun.live_search_status}</Badge></CardAction>
        </CardHeader>
        <CardContent className="space-y-2">
          {modelRun.results.map((item) => (
            <button
              key={item.question_id}
              type="button"
              onClick={() => onSelect(item.question_id)}
              aria-pressed={selected === item.question_id}
              className="w-full rounded-xl border p-3 text-left transition-colors hover:bg-muted/60 aria-pressed:bg-accent"
            >
              <span className="mb-1 flex items-center justify-between gap-2">
                <Badge variant="outline">{item.question_id}</Badge>
                <span className="text-xs text-muted-foreground">{item.company_source_urls.length} company · {item.third_party_source_urls.length} third-party</span>
              </span>
              <strong className="block text-sm font-medium leading-5">{item.question}</strong>
            </button>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardDescription>{result.question_id} · Domain {result.domain_cited ? 'cited' : result.domain_mentioned ? 'mentioned' : 'absent'}</CardDescription>
          <CardTitle>{result.question}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">Returned answer</p>
            <p className="text-sm leading-6">{result.answer}</p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">Company sources</p>
              <div className="space-y-2">
                {result.company_source_urls.map((url) => (
                  <a key={url} href={url} target="_blank" rel="noreferrer" className="block truncate rounded-lg bg-muted/60 px-3 py-2 text-xs hover:bg-muted">{url}</a>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">Third-party sources</p>
              <div className="space-y-2">
                {result.third_party_source_urls.length ? result.third_party_source_urls.map((url) => (
                  <a key={url} href={url} target="_blank" rel="noreferrer" className="block truncate rounded-lg bg-muted/60 px-3 py-2 text-xs hover:bg-muted">{url}</a>
                )) : <p className="text-sm text-muted-foreground">No third-party source returned.</p>}
              </div>
            </div>
          </div>

          <details className="rounded-xl border p-4">
            <summary className="cursor-pointer text-sm font-medium">Key claims · {result.key_claims.length}</summary>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-muted-foreground">
              {result.key_claims.map((claim) => <li key={claim}>{claim}</li>)}
            </ul>
          </details>
          <details className="rounded-xl border p-4">
            <summary className="cursor-pointer text-sm font-medium">Uncertainties · {result.uncertainties.length}</summary>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-muted-foreground">
              {result.uncertainties.map((uncertainty) => <li key={uncertainty}>{uncertainty}</li>)}
            </ul>
          </details>
        </CardContent>
      </Card>
    </div>
  );
}

function PriorityRail() {
  return (
    <aside className="space-y-4">
      <div className="flex items-center justify-between"><h2 className="text-sm font-semibold">Priority findings</h2><Badge variant="destructive">Manual review</Badge></div>
      {priorityFindings.map((finding) => (
        <Card key={finding.title} size="sm">
          <CardHeader><Badge variant="destructive">Critical</Badge><CardTitle>{finding.title}</CardTitle><CardDescription>{finding.detail}</CardDescription></CardHeader>
          <CardContent className="flex items-center justify-between border-t pt-3 text-xs"><span className="text-muted-foreground">Affected scope</span><span className="font-mono font-medium">{finding.breadth}</span></CardContent>
        </Card>
      ))}
    </aside>
  );
}

function DerivedFamilyView({ family }: { family: Family }) {
  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
      <div className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <ScoreCard label="Derived readiness" value={`${family.score}%`} context="Pass + half-weighted partial, applicable automated checks" />
          <ScoreCard label="Pass results" value={String(family.pass)} context="Across 16 audited pages" />
          <ScoreCard label="Fail results" value={String(family.fail)} context="Across applicable checks" />
          <ScoreCard label="Manual reviews" value={String(family.manual)} context="Human judgment still required" />
        </div>
        <Card>
          <CardHeader><CardDescription>Aggregated from page-level audit findings</CardDescription><CardTitle>Coverage by audit category</CardTitle></CardHeader>
          <CardContent className="space-y-5">
            {family.categories.map((category) => (
              <Progress key={category.name} value={category.score}>
                <ProgressLabel>{category.name}</ProgressLabel>
                <ProgressValue>{category.score}% · {category.affected} fail/partial results</ProgressValue>
              </Progress>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardDescription>Drill-down model</CardDescription><CardTitle>Category → check → affected page</CardTitle></CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            {family.categories.map((category, index) => (
              <button key={category.name} type="button" className="flex items-center gap-3 rounded-xl border p-4 text-left transition-colors hover:bg-muted/60">
                <span className="flex size-9 items-center justify-center rounded-lg bg-primary/10 font-mono text-sm font-medium text-primary">{String(index + 1).padStart(2, '0')}</span>
                <span className="min-w-0 flex-1"><strong className="block font-medium">{category.name}</strong><small className="text-xs text-muted-foreground">{category.affected} fail/partial results</small></span>
                <ChevronRight className="size-4 text-muted-foreground" />
              </button>
            ))}
          </CardContent>
        </Card>
      </div>
      <PriorityRail />
    </div>
  );
}

function SeoView() {
  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <ScoreCard label="Observed keywords" value="16" context="GSC discovery period" />
        <ScoreCard label="Ranking pages" value="15" context="Across observed queries" />
        <ScoreCard label="Impressions" value="710" context="Feb 25 – Aug 17, 2026" />
        <ScoreCard label="Clicks / CTR" value="0 / 0%" context="Position range 1–99" />
      </div>
      <Card>
        <CardHeader><CardDescription>Highest-impression query/page pairs</CardDescription><CardTitle>Organic search visibility</CardTitle><CardAction><Badge variant="outline">8 of 34 rows</Badge></CardAction></CardHeader>
        <CardContent className="overflow-x-auto px-0">
          <div className="min-w-[760px]">
            <div className="grid grid-cols-[minmax(220px,1.2fr)_minmax(220px,1fr)_90px_70px_70px_100px] gap-2 border-b px-4 pb-2 text-[11px] uppercase tracking-wider text-muted-foreground"><span>Query</span><span>Landing page</span><span className="text-right">Impr.</span><span className="text-right">Best</span><span className="text-right">Latest</span><span>Status</span></div>
            {searchRows.map((row, index) => (
              <div key={`${row.query}-${row.page}-${index}`} className="grid grid-cols-[minmax(220px,1.2fr)_minmax(220px,1fr)_90px_70px_70px_100px] gap-2 border-b px-4 py-3 text-sm">
                <span>{row.query}</span><span className="truncate text-muted-foreground">{row.page}</span><span className="text-right font-mono">{row.impressions}</span><span className="text-right font-mono">{row.best}</span><span className="text-right font-mono">{row.latest}</span><span><Badge variant="outline">{row.status}</Badge></span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function OnsiteView() {
  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <ScoreCard label="Discovered" value="17" context="Latest technical crawl" />
        <ScoreCard label="Crawled" value="17" context="All discovered pages" />
        <ScoreCard label="Failed" value="0" context="Crawl status completed" />
        <ScoreCard label="Technical issues" value="24" context="1 high · 6 medium · 17 low" />
      </div>
      <div className="grid gap-5 lg:grid-cols-[280px_minmax(0,1fr)]">
        <Card>
          <CardHeader><CardDescription>Issue distribution</CardDescription><CardTitle>Severity</CardTitle></CardHeader>
          <CardContent className="space-y-5">
            <Progress value={4}><ProgressLabel>High</ProgressLabel><ProgressValue>1</ProgressValue></Progress>
            <Progress value={25}><ProgressLabel>Medium</ProgressLabel><ProgressValue>6</ProgressValue></Progress>
            <Progress value={71}><ProgressLabel>Low</ProgressLabel><ProgressValue>17</ProgressValue></Progress>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardDescription>Grouped from 24 report rows</CardDescription><CardTitle>Technical issue inventory</CardTitle></CardHeader>
          <CardContent className="px-0">
            {technicalIssues.map((issue, index) => (
              <div key={`${issue.issue}-${index}`} className="grid grid-cols-[90px_minmax(180px,.8fr)_minmax(220px,1fr)] gap-3 border-b px-4 py-3 text-sm">
                <Badge variant={issue.severity === 'High' ? 'destructive' : issue.severity === 'Medium' ? 'secondary' : 'outline'}>{issue.severity}</Badge>
                <span className="font-medium">{issue.issue}</span><span className="truncate text-muted-foreground">{issue.page}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function Home() {
  const [familyId, setFamilyId] = useState('ai');
  const [scoreBand, setScoreBand] = useState('all');
  const [selectedPage, setSelectedPage] = useState('/');
  const [selectedQuestion, setSelectedQuestion] = useState('Q1');
  const family = useMemo(() => families.find((item) => item.id === familyId) ?? families[0], [familyId]);

  const filteredScores = useMemo(() => pageScores.filter((item) => {
    if (scoreBand === 'low') return item.combined < 75;
    if (scoreBand === 'mid') return item.combined >= 75 && item.combined < 80;
    if (scoreBand === 'high') return item.combined >= 80;
    return true;
  }), [scoreBand]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-40 flex h-14 items-center border-b bg-background/90 px-4 backdrop-blur-md lg:px-6">
        <div className="flex items-center gap-2.5">
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground"><Gauge className="size-4" /></span>
          <div className="leading-tight"><p className="text-sm font-semibold">Observer Intelligence</p><p className="text-[11px] text-muted-foreground">Representation audit</p></div>
        </div>
        <NativeSelect className="ml-3 lg:hidden" size="sm" value={familyId} onChange={(event) => setFamilyId(event.target.value)} aria-label="Report family">
          {families.map((item) => <NativeSelectOption key={item.id} value={item.id}>{item.name}</NativeSelectOption>)}
        </NativeSelect>
        <div className="ml-auto flex items-center gap-2">
          <div className="hidden items-center gap-2 rounded-lg border bg-muted/40 px-3 py-1.5 md:flex"><Building2 className="size-3.5 text-muted-foreground" /><span className="text-xs font-medium">povarchik.com</span><span className="text-xs text-muted-foreground">Run 14 · Aug 22</span></div>
          <Button variant="outline" size="sm"><Download data-icon="inline-start" /> Export</Button>
        </div>
      </header>

      <div className="grid min-h-[calc(100vh-3.5rem)] lg:grid-cols-[248px_minmax(0,1fr)]">
        <Sidebar familyId={familyId} onChange={setFamilyId} />
        <main className="min-w-0 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
          <div className="mx-auto max-w-[1480px]">
            <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
              <div className="max-w-3xl">
                <div className="mb-2 flex items-center gap-2"><Badge variant="outline">{family.number}</Badge><span className="text-xs text-muted-foreground">{family.owners}</span></div>
                <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{family.name}</h1>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">{family.question}</p>
              </div>
              <div className="flex items-center gap-2"><Badge variant="secondary">Report data · Aug 22, 2026</Badge><Badge variant="outline">Audit partial</Badge></div>
            </div>

            {family.id === 'seo' ? <SeoView /> : family.id === 'onsite' ? <OnsiteView /> : family.id !== 'ai' ? <DerivedFamilyView family={family} /> : (
              <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
                <div className="min-w-0 space-y-5">
                  <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                    <ScoreCard label="Model runs" value="1 / 3" context="ChatGPT received · Gemini and Claude pending" />
                    <ScoreCard label="Questions answered" value="4 / 4" context="One complete provider run" />
                    <ScoreCard label="Domain cited" value="4 / 4" context="povarchik.com cited in every answer" />
                    <ScoreCard label="Live search" value="Available" context="GPT-5.6 Sol · Aug 28, 2026" />
                  </div>

                  <Tabs defaultValue="study">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <TabsList variant="line"><TabsTrigger value="study">AI study</TabsTrigger><TabsTrigger value="readiness">Readiness view</TabsTrigger><TabsTrigger value="pages">Pages & scores</TabsTrigger><TabsTrigger value="search">Search evidence</TabsTrigger></TabsList>
                      <NativeSelect value={scoreBand} onChange={(event) => setScoreBand(event.target.value)} size="sm" aria-label="Combined score band"><NativeSelectOption value="all">All page scores</NativeSelectOption><NativeSelectOption value="low">Below 75</NativeSelectOption><NativeSelectOption value="mid">75–79</NativeSelectOption><NativeSelectOption value="high">80 and above</NativeSelectOption></NativeSelect>
                    </div>

                    <TabsContent value="study" className="mt-3">
                      <AiStudyView selected={selectedQuestion} onSelect={setSelectedQuestion} />
                    </TabsContent>

                    <TabsContent value="readiness" className="mt-3 space-y-5">
                      <Card>
                        <CardHeader>
                          <CardDescription>Reported page-level scores</CardDescription><CardTitle>GEO and AEO readiness by page</CardTitle>
                          <CardAction><div className="flex gap-3 text-xs text-muted-foreground"><span className="flex items-center gap-1"><i className="size-2 rounded-full bg-[var(--chart-cited)]" />GEO</span><span className="flex items-center gap-1"><i className="size-2 rounded-full bg-[var(--chart-mentioned)]" />AEO</span></div></CardAction>
                        </CardHeader>
                        <CardContent><ReadinessChart band={scoreBand} /></CardContent>
                      </Card>
                      <Card><CardHeader><CardDescription>Pass 1,056 · Partial 110 · Fail 390 · Manual review 186</CardDescription><CardTitle>Audited page scorecard</CardTitle><CardAction><Badge variant="outline">{filteredScores.length} pages</Badge></CardAction></CardHeader><CardContent className="px-0"><PageScoreTable selected={selectedPage} onSelect={setSelectedPage} rows={filteredScores} /></CardContent></Card>
                    </TabsContent>

                    <TabsContent value="pages" className="mt-3 grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
                      <Card><CardHeader><CardDescription>16 pages in GEO/AEO audit run #14</CardDescription><CardTitle>Page-level readiness</CardTitle></CardHeader><CardContent className="px-0"><PageScoreTable selected={selectedPage} onSelect={setSelectedPage} rows={filteredScores} /></CardContent></Card>
                      <PageEvidence page={selectedPage} />
                    </TabsContent>

                    <TabsContent value="search" className="mt-3">
                      <SeoView />
                    </TabsContent>
                  </Tabs>
                </div>
                <PriorityRail />
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
