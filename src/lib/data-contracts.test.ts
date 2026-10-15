import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parseContextSnapshot, parseResearchBundle, parseResearchSnapshot } from './data-contracts.ts'

test('research parser rejects empty and unversioned payloads', () => {
  assert.throws(() => parseResearchSnapshot({}), /mode/i)
  assert.throws(() => parseResearchSnapshot({ mode: 'VERIFIED_HISTORICAL' }), /schema/i)
})

test('research parser rejects synthetic mode disguised with another label', () => {
  assert.throws(() => parseResearchSnapshot({ mode: 'LIVE' }), /mode/i)
})

test('verified snapshots cannot omit clean data identity and source lineage', () => {
  assert.throws(() => parseResearchSnapshot({
    mode: 'VERIFIED_HISTORICAL', schema_version: '1.0.0', engine_version: '0.2.0',
    content_sha256: 'a'.repeat(64), lineage: {},
  }), /clean-dataset identity/i)
})

test('context parser exposes an explicit error state for partial payloads', () => {
  assert.throws(() => parseContextSnapshot({ mode: 'SUPPLEMENTARY_REFERENCE' }), /incomplete/i)
})

test('generated demo artifact has typed, expiry-aware test results and an honest mode', () => {
  const artifact = JSON.parse(readFileSync('public/data/demo-research.v1.json', 'utf8')) as unknown
  const bundle = parseResearchBundle(artifact)
  assert.equal(bundle.mode, 'DEMO')
  const snapshot = bundle.analyses['GOLDTEN/GOLDM']['40']
  assert.equal(snapshot.pair.candidate_expiry, '2026-10-30')
  assert.equal(snapshot.contract_specifications.candidate.quoted_grams, '10')
  assert.ok(snapshot.partition_simulations.test.daily.length > 0)
})
