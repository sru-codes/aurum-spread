import { useEffect, useRef } from 'react'
import { ArrowDown, ArrowRight, ArrowUpRight, Check, CircleHelp, FileCheck2, Scale, ShieldCheck } from 'lucide-react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import Lenis from 'lenis'
import './LandingPage.css'

gsap.registerPlugin(ScrollTrigger)

const contracts = [
  { symbol: 'GOLDM', detail: 'A larger gold contract' },
  { symbol: 'GOLDTEN', detail: 'A different gold contract' },
  { symbol: 'GOLDGUINEA', detail: 'A smaller gold contract' },
  { symbol: 'GOLDPETAL', detail: 'A small-unit gold contract' },
]

const questions = [
  {
    number: '01',
    title: 'Are we comparing the same amount of gold?',
    copy: 'Contracts can quote different weights and gold purity. Aurum converts them to a like-for-like fine-gold price before comparing.',
    icon: <Scale aria-hidden="true" />,
  },
  {
    number: '02',
    title: 'Do the contracts expire at different times?',
    copy: 'A later expiry can reasonably cost more because time, funding, and delivery matter. That carry is shown separately from the remaining gap.',
    icon: <FileCheck2 aria-hidden="true" />,
  },
  {
    number: '03',
    title: 'Is anything unusual left after that?',
    copy: 'Only then does the research test the difference—and it can still conclude that there is not enough evidence for a signal.',
    icon: <CircleHelp aria-hidden="true" />,
  },
]

const workflow = [
  {
    number: '01',
    title: 'Start with the exchange file',
    copy: 'Use an official MCX daily report. Aurum checks its date and contract rows, keeps the original file, and reports anything it rejects.',
    note: 'Official source · checked import',
  },
  {
    number: '02',
    title: 'Make the comparison fair',
    copy: 'Prices are adjusted for quoted weight and purity. Every contract keeps its own expiry, so one month is never accidentally mixed with another.',
    note: 'Same gold basis · expiry stays visible',
  },
  {
    number: '03',
    title: 'Ask whether the gap is unusual',
    copy: 'The model looks only at earlier sessions, then checks liquidity, costs, and contract timing. No future prices are used to explain the past.',
    note: 'Past-only test · costs shown separately',
  },
]

export default function LandingPage() {
  const storyRef = useRef<HTMLDivElement>(null)
  const progressRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduceMotion) return

    const lenis = new Lenis({ autoRaf: false, smoothWheel: true, lerp: 0.09 })
    const updateScroll = () => ScrollTrigger.update()
    const tick = (time: number) => lenis.raf(time * 1000)
    lenis.on('scroll', updateScroll)
    gsap.ticker.add(tick)
    gsap.ticker.lagSmoothing(0)

    const context = gsap.context(() => {
      gsap.utils.toArray<HTMLElement>('[data-reveal]').forEach((element) => {
        gsap.fromTo(element,
          { autoAlpha: 0, y: 24 },
          {
            autoAlpha: 1,
            y: 0,
            duration: 0.72,
            ease: 'power3.out',
            immediateRender: false,
            scrollTrigger: { trigger: element, start: 'top 84%', once: true },
          },
        )
      })

      if (progressRef.current && storyRef.current) {
        gsap.fromTo(progressRef.current,
          { scaleY: 0 },
          {
            scaleY: 1,
            ease: 'none',
            scrollTrigger: { trigger: storyRef.current, start: 'top 68%', end: 'bottom 72%', scrub: true },
          },
        )
      }
    }, storyRef)

    ScrollTrigger.refresh()
    return () => {
      context.revert()
      lenis.off('scroll', updateScroll)
      gsap.ticker.remove(tick)
      gsap.ticker.lagSmoothing(500, 33)
      lenis.destroy()
    }
  }, [])

  return <div className="landing-shell">
    <a className="landing-skip" href="#main-content">Skip to story</a>
    <header className="landing-nav">
      <a className="landing-brand" href="/" aria-label="Aurum Spread home">
        <span className="landing-brand-mark" aria-hidden="true">Au</span>
        <span><strong>Aurum Spread</strong><small>Commodity research, made clear</small></span>
      </a>
      <nav aria-label="Main navigation">
        <a href="#why">The idea</a>
        <a href="#how-it-works">How it works</a>
      </nav>
      <a className="landing-nav-cta" href="/dashboard">Open the panel <ArrowUpRight size={15} aria-hidden="true" /></a>
    </header>

    <main id="main-content">
      <section className="landing-hero" aria-labelledby="landing-title">
        <div className="landing-hero-copy">
          <span className="landing-kicker"><i /> A simple guide to Aurum Spread</span>
          <h1 id="landing-title">Gold prices can differ.<br /><em>Here’s how to tell why.</em></h1>
          <p>Aurum Spread helps you compare MCX gold contracts fairly—so a normal difference in weight, purity, or expiry isn’t mistaken for an opportunity.</p>
          <div className="landing-hero-actions">
            <a className="button-gold" href="#why">Follow the story <ArrowDown size={16} aria-hidden="true" /></a>
            <a className="button-text" href="/dashboard">I know the basics <ArrowRight size={15} aria-hidden="true" /></a>
          </div>
          <p className="landing-hero-footnote"><ShieldCheck size={14} aria-hidden="true" /> Research and education only · No trading or order placement</p>
        </div>

        <div className="comparison-illustration" aria-label="Conceptual illustration: different MCX gold contracts are normalized before comparison; no live prices shown">
          <div className="illustration-head"><span>THE SIMPLE IDEA</span><span>01 / 03</span></div>
          <div className="illustration-title">Different contracts.<br /><strong>One fair comparison.</strong></div>
          <div className="contract-stack">
            {contracts.map((contract, index) => <div className="contract-row" key={contract.symbol}>
              <span className={`contract-swatch swatch-${index + 1}`} aria-hidden="true" />
              <strong>{contract.symbol}</strong>
              <span>{contract.detail}</span>
            </div>)}
          </div>
          <div className="normalize-arrow"><span /> <ArrowDown size={14} aria-hidden="true" /><span /></div>
          <div className="comparison-result"><span className="result-mark" aria-hidden="true"><Check size={15} /></span><div><strong>Compare like with like</strong><small>Weight · purity · expiry</small></div><span className="result-caption">NOT LIVE DATA</span></div>
          <div className="illustration-foot"><span>Illustration only</span><span>No market values shown</span></div>
        </div>
        <a className="hero-scroll-cue" href="#why"><span>Scroll to understand</span><ArrowDown size={14} aria-hidden="true" /></a>
      </section>

      <section className="landing-section why-section" id="why" aria-labelledby="why-title">
        <div className="section-intro" data-reveal>
          <span className="landing-kicker"><i /> First, the problem</span>
          <h2 id="why-title">A price gap is a clue.<br /><em>Not an answer.</em></h2>
          <p>Two gold futures contracts can show different prices even when nothing is wrong. Before calling one “cheap,” we need to understand what is actually being compared.</p>
        </div>
        <div className="question-list" ref={storyRef}>
          <div className="question-progress" aria-hidden="true"><span ref={progressRef} /></div>
          {questions.map((question) => <article className="question-row" data-reveal key={question.number}>
            <span className="question-number">{question.number}</span>
            <div className="question-icon">{question.icon}</div>
            <div className="question-copy"><h3>{question.title}</h3><p>{question.copy}</p></div>
            <ArrowRight className="question-arrow" size={17} aria-hidden="true" />
          </article>)}
        </div>
      </section>

      <section className="plain-language-band" data-reveal>
        <span className="band-symbol" aria-hidden="true">“</span>
        <p>In plain English: <strong>first make prices comparable, then ask whether the leftover difference is surprising.</strong></p>
        <span className="band-caption">THAT’S THE WHOLE IDEA</span>
      </section>

      <section className="landing-section workflow-section" id="how-it-works" aria-labelledby="workflow-title">
        <div className="section-intro" data-reveal>
          <span className="landing-kicker"><i /> Then, the process</span>
          <h2 id="workflow-title">From an exchange file<br /><em>to a clearer decision.</em></h2>
          <p>No mystery score. The panel shows what data went in, what was adjusted, and why it did—or didn’t—pass each check.</p>
        </div>
        <div className="workflow-grid">
          {workflow.map((step) => <article className="workflow-card" data-reveal key={step.number}>
            <span className="workflow-number">{step.number}</span>
            <h3>{step.title}</h3>
            <p>{step.copy}</p>
            <div className="workflow-note"><Check size={13} aria-hidden="true" /> {step.note}</div>
          </article>)}
        </div>
      </section>

      <section className="reader-section" aria-labelledby="reader-title">
        <div className="reader-copy" data-reveal>
          <span className="landing-kicker"><i /> When you open the panel</span>
          <h2 id="reader-title">You don’t need to be a trader<br /><em>to read the answer.</em></h2>
          <p>Choose two contracts and their expiry dates. Pick how much history to compare. Then read the plain verdict and the checks behind it.</p>
          <ol className="reader-steps">
            <li><span>1</span><div><strong>Choose a pair</strong><small>Pick the gold contracts and expiry dates.</small></div></li>
            <li><span>2</span><div><strong>Choose a time window</strong><small>See how the comparison changes over history.</small></div></li>
            <li><span>3</span><div><strong>Read the checks</strong><small>Understand the result—or why there is no signal.</small></div></li>
          </ol>
          <a className="button-gold" href="/dashboard">Open the research panel <ArrowRight size={16} aria-hidden="true" /></a>
        </div>
        <div className="panel-preview" data-reveal aria-label="Illustration of the research panel layout, not a live result">
          <div className="preview-topbar"><div className="preview-brand"><span className="landing-brand-mark">Au</span><strong>Aurum Spread</strong></div><span className="preview-tag">PANEL PREVIEW</span></div>
          <div className="preview-heading"><span>FUTURES MONITOR</span><span>DEMO DATA IS LABELED</span></div>
          <div className="preview-question">What does the evidence say?</div>
          <div className="preview-verdict"><span className="preview-status-dot" /><div><strong>No signal</strong><small>A valid result when the evidence isn’t strong enough.</small></div></div>
          <div className="preview-gates"><span><i /> Price comparison</span><span><i /> Expiry and carry</span><span><i /> Liquidity and costs</span></div>
          <div className="preview-rule"><span />The panel explains each check. It never promises a profitable trade.</div>
          <div className="preview-footer"><span>Illustrative layout</span><span>No live market values</span></div>
        </div>
      </section>

      <section className="closing-section" data-reveal>
        <span className="landing-kicker"><i /> Ready when you are</span>
        <h2>Curious what the contracts<br />are saying <em>today?</em></h2>
        <p>Open the research panel. Start with the clearly labeled demo, or use a verified historical dataset when one has been imported.</p>
        <a className="button-gold button-light" href="/dashboard">Go to the research panel <ArrowUpRight size={16} aria-hidden="true" /></a>
        <span className="closing-note">Research and education only · No broker connection · No orders placed</span>
      </section>
    </main>

    <footer className="landing-footer"><a className="landing-brand" href="/" aria-label="Aurum Spread home"><span className="landing-brand-mark">Au</span><span><strong>Aurum Spread</strong><small>Find the spread. Prove the edge.</small></span></a><span>Built for Hack in Hills ’26 · Problem 03</span><a href="/dashboard">Research panel <ArrowUpRight size={14} aria-hidden="true" /></a></footer>
  </div>
}
