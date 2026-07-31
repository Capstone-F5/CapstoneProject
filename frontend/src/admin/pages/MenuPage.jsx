import { useRef, useState, useEffect } from 'react'
import {
  fetchAdminMenu,
  updateMenuItem, createMenuItem, deleteMenuItem,
  createCategory, updateCategory, deleteCategory,
  createMenuOption, updateMenuOption, deleteMenuOption,
  uploadMenuImage,
} from '../api/adminApi.js'

const OPTION_GROUPS = [
  { value: 'SET_UPGRADE', label: '단품/세트' },
  { value: 'EXCLUDE',     label: '제외하기'  },
  { value: 'SET_SIDE',    label: '사이드'    },
  { value: 'SET_DRINK',   label: '음료수'    },
]
const GROUP_LABEL = Object.fromEntries(OPTION_GROUPS.map(g => [g.value, g.label]))

// ─── Toggle ─── (div 기반, label→input 이중클릭 없음) ──────────────────────
function Toggle({ checked, onChange }) {
  return (
    <div
      role="switch"
      aria-checked={checked}
      className="toggle"
      onClick={e => { e.stopPropagation(); onChange(!checked) }}
      style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center' }}
    >
      <div className="toggle-track" style={{ background: checked ? '#744032' : '#ccc' }} />
      <div className="toggle-thumb" />
    </div>
  )
}

// ─── ImageUploader ──────────────────────────────────────────────────────────
function ImageUploader({ url, onChange }) {
  const fileRef = useRef(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  const handleFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setError('')
    try {
      const res = await uploadMenuImage(file)
      onChange(res.url)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  return (
    <div style={{ marginBottom: 16 }}>
      <div className="form-label">이미지</div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
        <div style={{
          width: 80, height: 80, borderRadius: 8, border: '1px solid #e8e8e8',
          background: '#f5f5f5', overflow: 'hidden', flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 24,
        }}>
          {url
            ? <img src={url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            : '🍔'
          }
        </div>
        <div style={{ flex: 1 }}>
          <input
            className="form-input"
            placeholder="이미지 URL 직접 입력"
            value={url ?? ''}
            onChange={e => onChange(e.target.value || null)}
            style={{ marginBottom: 8 }}
          />
          <button
            type="button"
            className="btn-outline btn-sm"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            style={{ fontSize: 12 }}
          >
            {uploading ? '업로드 중…' : '파일 업로드'}
          </button>
          <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handleFile} />
          {error && <div style={{ color: '#c00', fontSize: 12, marginTop: 4 }}>{error}</div>}
        </div>
      </div>
    </div>
  )
}

// ─── EditCategoryModal ── 생성/수정 겸용 ────────────────────────────────────
function EditCategoryModal({ category, onClose, onSave }) {
  const isEdit = !!category
  const [form, setForm] = useState({
    name_ko:       category?.name_ko       ?? '',
    name_en:       category?.name_en       ?? '',
    display_order: category?.display_order ?? 0,
  })
  const [loading, setLoading] = useState(false)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSave = async () => {
    if (!form.name_ko.trim()) { alert('한국어 이름을 입력하세요'); return }
    if (!form.name_en.trim()) { alert('영어 이름을 입력하세요'); return }
    setLoading(true)
    try {
      await onSave({ ...form, display_order: Number(form.display_order) })
      onClose()
    } catch (e) {
      alert(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay">
      <div className="modal-box" style={{ width: 400 }}>
        <div className="modal-title">{isEdit ? '카테고리 수정' : '카테고리 추가'}</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">이름 (한국어) *</label>
            <input className="form-input" value={form.name_ko} onChange={e => set('name_ko', e.target.value)} autoFocus />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">이름 (영어) *</label>
            <input className="form-input" value={form.name_en} onChange={e => set('name_en', e.target.value)} />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">표시 순서</label>
          <input className="form-input" type="number" min="0" value={form.display_order}
            onChange={e => set('display_order', e.target.value)} />
        </div>
        <div className="modal-footer">
          <button className="btn-outline" onClick={onClose}>취소</button>
          <button className="btn-primary" onClick={handleSave} disabled={loading}>
            {loading ? '저장 중…' : isEdit ? '수정' : '추가'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── EditItemModal ──────────────────────────────────────────────────────────
function EditItemModal({ item, categoryId, categories, onClose, onSave }) {
  const [form, setForm] = useState({
    name_ko:       item?.name_ko       ?? '',
    name_en:       item?.name_en       ?? '',
    base_price:    item?.base_price    ?? '',
    description:   item?.description   ?? '',
    image_url:     item?.image_url     ?? null,
    set_image_url: item?.set_image_url ?? null,
    is_available:  item?.is_available  ?? true,
    is_popular:    item?.is_popular    ?? false,
    is_new:        item?.is_new        ?? false,
    category_id:   item?.category_id ?? categoryId ?? categories?.[0]?.id ?? '',
  })
  const [loading, setLoading] = useState(false)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSave = async () => {
    if (!form.name_ko.trim()) { alert('한국어 이름을 입력하세요'); return }
    if (!form.name_en.trim()) { alert('영어 이름을 입력하세요'); return }
    if (!form.base_price)     { alert('가격을 입력하세요'); return }
    setLoading(true)
    try {
      await onSave(item?.id, { ...form, base_price: Number(form.base_price) })
      onClose()
    } catch (e) {
      alert(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay">
      <div className="modal-box" style={{ width: 520, maxHeight: '90vh', overflowY: 'auto' }}>
        <div className="modal-title">{item ? '메뉴 수정' : '메뉴 추가'}</div>

        <div className="form-group">
          <label className="form-label">카테고리</label>
          <select className="form-input" value={form.category_id} onChange={e => set('category_id', e.target.value)}>
            {(categories ?? []).map(c => <option key={c.id} value={c.id}>{c.name_ko}</option>)}
          </select>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">이름 (한국어) *</label>
            <input className="form-input" value={form.name_ko} onChange={e => set('name_ko', e.target.value)} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">이름 (영어) *</label>
            <input className="form-input" value={form.name_en} onChange={e => set('name_en', e.target.value)} />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">기본 가격 (원) *</label>
          <input className="form-input" type="number" min="0" value={form.base_price}
            onChange={e => set('base_price', e.target.value)} />
        </div>

        <div className="form-group">
          <label className="form-label">설명</label>
          <input className="form-input" value={form.description} onChange={e => set('description', e.target.value)} />
        </div>

        <ImageUploader url={form.image_url} onChange={v => set('image_url', v)} />

        <div className="form-group">
          <label className="form-label">세트 이미지 URL (없으면 기본 이미지 사용)</label>
          <input className="form-input" placeholder="/images/sets/..." value={form.set_image_url ?? ''}
            onChange={e => set('set_image_url', e.target.value || null)} />
        </div>

        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', marginBottom: 20 }}>
          {[['is_available','판매중'], ['is_popular','인기'], ['is_new','신메뉴']].map(([key, label]) => (
            <label key={key} style={{ display:'flex', alignItems:'center', gap:6, cursor:'pointer', fontSize:13 }}>
              <input type="checkbox" checked={form[key]} onChange={e => set(key, e.target.checked)} />
              {label}
            </label>
          ))}
        </div>

        <div className="modal-footer">
          <button className="btn-outline" onClick={onClose}>취소</button>
          <button className="btn-primary" onClick={handleSave} disabled={loading}>
            {loading ? '저장 중…' : '저장'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── EditOptionModal ─────────────────────────────────────────────────────────
function EditOptionModal({ option, itemId, defaultGroup, onClose, onSave }) {
  const [form, setForm] = useState({
    name_ko:          option?.name_ko          ?? '',
    name_en:          option?.name_en          ?? '',
    additional_price: option?.additional_price != null ? Number(option.additional_price) : 0,
    option_group:     option?.option_group     ?? defaultGroup ?? 'EXCLUDE',
    display_order:    option?.display_order    ?? 0,
    is_available:     option?.is_available     ?? true,
  })
  const [loading, setLoading] = useState(false)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSave = async () => {
    if (!form.name_ko.trim()) { alert('한국어 이름을 입력하세요'); return }
    if (!form.name_en.trim()) { alert('영어 이름을 입력하세요'); return }
    setLoading(true)
    try {
      await onSave(itemId, option?.id, { ...form, additional_price: Number(form.additional_price) })
      onClose()
    } catch (e) {
      alert(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay">
      <div className="modal-box" style={{ width: 440 }}>
        <div className="modal-title">{option ? '옵션 수정' : '옵션 추가'}</div>

        <div className="form-group">
          <label className="form-label">옵션 그룹</label>
          <select className="form-input" value={form.option_group} onChange={e => set('option_group', e.target.value)}>
            {OPTION_GROUPS.map(g => <option key={g.value} value={g.value}>{g.label}</option>)}
          </select>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">이름 (한국어) *</label>
            <input className="form-input" value={form.name_ko} onChange={e => set('name_ko', e.target.value)} autoFocus />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">이름 (영어) *</label>
            <input className="form-input" value={form.name_en} onChange={e => set('name_en', e.target.value)} />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">추가 가격 (원)</label>
            <input className="form-input" type="number" min="0" value={form.additional_price}
              onChange={e => set('additional_price', e.target.value)} />
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">표시 순서</label>
            <input className="form-input" type="number" min="0" value={form.display_order}
              onChange={e => set('display_order', Number(e.target.value))} />
          </div>
        </div>

        <label style={{ display:'flex', alignItems:'center', gap:8, cursor:'pointer', fontSize:13, marginBottom:20 }}>
          <input type="checkbox" checked={form.is_available} onChange={e => set('is_available', e.target.checked)} />
          판매 가능
        </label>

        <div className="modal-footer">
          <button className="btn-outline" onClick={onClose}>취소</button>
          <button className="btn-primary" onClick={handleSave} disabled={loading}>
            {loading ? '저장 중…' : '저장'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── OptionGroupSection ── 그룹별 섹션 ──────────────────────────────────────
function OptionGroupSection({ group, options, item, onAdd, onEdit, onDelete, onToggle, deletingOpt }) {
  const groupOptions = options.filter(o => o.option_group === group.value)
    .sort((a, b) => a.display_order - b.display_order)

  return (
    <div style={{ borderBottom: '1px solid #f0f0f0' }}>
      {/* 섹션 헤더 */}
      <div style={{
        padding: '10px 20px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        background: '#fafafa',
      }}>
        <span style={{
          fontSize: 12, fontWeight: 700, color: '#744032',
          padding: '2px 10px', background: '#f0ebe8', borderRadius: 999,
        }}>
          {group.label}
        </span>
        <button
          className="btn-outline btn-sm"
          style={{ fontSize: 11, padding: '3px 10px' }}
          onClick={() => onAdd(group.value)}
        >
          + 추가
        </button>
      </div>

      {/* 옵션 목록 */}
      {groupOptions.length === 0 ? (
        <div style={{ padding: '10px 20px', fontSize: 13, color: '#bbb' }}>
          {group.label} 항목이 없습니다
        </div>
      ) : (
        <table className="data-table" style={{ margin: 0 }}>
          <thead>
            <tr>
              <th>한국어</th>
              <th>영어</th>
              <th style={{ width: 90 }}>추가금액</th>
              <th style={{ width: 60 }}>판매</th>
              <th style={{ width: 100 }}></th>
            </tr>
          </thead>
          <tbody>
            {groupOptions.map(opt => (
              <tr key={opt.id}>
                <td style={{ fontWeight: 500 }}>{opt.name_ko}</td>
                <td style={{ color: '#888', fontSize: 12 }}>{opt.name_en}</td>
                <td>
                  {Number(opt.additional_price) > 0
                    ? <span style={{ color: '#F5B800', fontWeight: 600 }}>+{Number(opt.additional_price).toLocaleString('ko-KR')}원</span>
                    : <span style={{ color: '#bbb' }}>-</span>
                  }
                </td>
                <td>
                  <Toggle
                    checked={opt.is_available}
                    onChange={() => onToggle(item, opt)}
                  />
                </td>
                <td style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <button className="btn-outline btn-sm" onClick={() => onEdit(opt)}>수정</button>
                  <button
                    className="btn-sm"
                    style={{ background: '#ffeaea', color: '#c00', border: '1px solid #ffc0c0', borderRadius: 6, cursor: 'pointer', fontSize: 12, padding: '4px 10px' }}
                    disabled={deletingOpt === opt.id}
                    onClick={() => {
                      if (confirm(`"${opt.name_ko}" 옵션을 삭제하시겠습니까?`))
                        onDelete(item.id, opt.id)
                    }}
                  >
                    {deletingOpt === opt.id ? '…' : '삭제'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

// ─── MenuPage ────────────────────────────────────────────────────────────────
export default function MenuPage() {
  const [data,          setData]          = useState(null)
  const [loading,       setLoading]       = useState(true)
  const [error,         setError]         = useState('')
  const [selectedCat,   setSelectedCat]   = useState(null)   // null = 전체
  const [selectedItem,  setSelectedItem]  = useState(null)
  const [editItem,      setEditItem]      = useState(undefined)  // undefined=숨김 | null=신규 | obj=수정
  const [editOption,    setEditOption]    = useState(undefined)  // undefined=숨김 | null=신규 | obj=수정
  const [editOptionGroup, setEditOptionGroup] = useState(null)   // editOption=null 일 때 기본 그룹
  // editCat: null=숨김, true=신규 추가, object=수정 대상 카테고리
  const [editCat,       setEditCat]       = useState(null)
  const [deletingOpt,   setDeletingOpt]   = useState(null)
  const [deletingItem,  setDeletingItem]  = useState(null)
  const [deletingCat,   setDeletingCat]   = useState(null)

  const load = () => {
    setLoading(true)
    fetchAdminMenu()
      .then(raw => { setData(raw) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleToggleAvailable = async (item) => {
    try { await updateMenuItem(item.id, { is_available: !item.is_available }); load() }
    catch (e) { alert(e.message) }
  }

  const handleToggleCatVisible = async (cat) => {
    try { await updateCategory(cat.id, { is_visible: !cat.is_visible }); load() }
    catch (e) { alert(e.message) }
  }

  const handleSaveItem = async (itemId, payload) => {
    if (itemId) await updateMenuItem(itemId, payload)
    else        await createMenuItem(payload)
    load()
  }

  const handleSaveOption = async (itemId, optionId, payload) => {
    if (optionId) await updateMenuOption(itemId, optionId, payload)
    else          await createMenuOption(itemId, payload)
    load()
  }

  const handleDeleteOption = async (itemId, optionId) => {
    setDeletingOpt(optionId)
    try { await deleteMenuOption(itemId, optionId); load() }
    catch (e) { alert(e.message) }
    finally { setDeletingOpt(null) }
  }

  const handleDeleteItem = async (itemId) => {
    setDeletingItem(itemId)
    try {
      await deleteMenuItem(itemId)
      if (selectedItem === itemId) setSelectedItem(null)
    } catch (e) {
      alert(e.message)
    } finally {
      setDeletingItem(null)
      load()
    }
  }

  const handleSaveCat = async (payload) => {
    if (editCat && editCat !== true) {
      await updateCategory(editCat.id, payload)
    } else {
      await createCategory({ ...payload, is_visible: true })
    }
    load()
  }

  const handleDeleteCat = async (cat) => {
    if (!confirm(`"${cat.name_ko}" 카테고리를 삭제하시겠습니까?\n메뉴가 있으면 삭제되지 않습니다.`)) return
    setDeletingCat(cat.id)
    try {
      await deleteCategory(cat.id)
      if (selectedCat === cat.id) setSelectedCat(null)
      load()
    } catch (e) {
      alert(e.message)
      load()
    } finally {
      setDeletingCat(null)
    }
  }

  const handleToggleOptionAvailable = async (item, opt) => {
    try { await updateMenuOption(item.id, opt.id, { is_available: !opt.is_available }); load() }
    catch (e) { alert(e.message) }
  }

  const openAddOption = (group) => {
    setEditOption(null)
    setEditOptionGroup(group)
  }

  const openEditOption = (opt) => {
    setEditOption(opt)
    setEditOptionGroup(null)
  }

  if (loading) return <div className="loading-text">메뉴 데이터 로딩 중…</div>
  if (error)   return <div className="loading-text" style={{ color:'#c00' }}>{error}</div>

  const allItems = Object.values(data?.menu_items ?? {}).flat()

  const displayItems = (() => {
    if (!selectedCat) return allItems
    const cat = data.categories.find(c => c.id === selectedCat)
    if (!cat) return allItems
    const catKey = cat.name_en?.toLowerCase() ?? ''
    return data.menu_items[catKey] ?? []
  })()

  const currentCat      = data?.categories?.find(c => c.id === selectedCat)
  const selectedItemFull = selectedItem ? allItems.find(i => i.id === selectedItem) ?? null : null

  return (
    <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>

      {/* ── 카테고리 패널 ── */}
      <div className="card" style={{ width: 200, minWidth: 200, padding: '8px 0' }}>
        <div style={{ padding: '12px 16px 8px', fontWeight: 700, fontSize: 14, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span>카테고리</span>
          <button
            className="btn-primary"
            style={{ fontSize: 11, padding: '3px 8px', borderRadius: 6 }}
            onClick={() => setEditCat(true)}
          >+ 추가</button>
        </div>

        {/* 전체 */}
        <div
          onClick={() => { setSelectedCat(null); setSelectedItem(null) }}
          style={{
            padding: '8px 16px', cursor: 'pointer',
            display: 'flex', alignItems: 'center',
            background:  !selectedCat ? '#fff5f0' : 'transparent',
            borderLeft:  !selectedCat ? '3px solid #744032' : '3px solid transparent',
            fontWeight:  !selectedCat ? 600 : 400,
            fontSize: 14, color: '#555',
          }}
        >
          전체
        </div>

        {(data?.categories ?? []).map(cat => (
          <div
            key={cat.id}
            onClick={() => { setSelectedCat(cat.id); setSelectedItem(null) }}
            style={{
              padding: '8px 16px 8px 12px', cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              background:  selectedCat === cat.id ? '#fff5f0' : 'transparent',
              borderLeft:  selectedCat === cat.id ? '3px solid #744032' : '3px solid transparent',
              fontWeight:  selectedCat === cat.id ? 600 : 400,
            }}
          >
            <span style={{ fontSize: 13, flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {cat.name_ko}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }} onClick={e => e.stopPropagation()}>
              <Toggle checked={cat.is_visible} onChange={() => handleToggleCatVisible(cat)} />
              <button
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#aaa', fontSize: 13, lineHeight: 1, padding: '1px 2px' }}
                onClick={() => setEditCat(cat)}
                title="카테고리 수정"
              >✎</button>
              <button
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#bbb', fontSize: 13, lineHeight: 1, padding: '1px 2px' }}
                disabled={deletingCat === cat.id}
                onClick={() => handleDeleteCat(cat)}
                title="삭제"
              >
                {deletingCat === cat.id ? '…' : '✕'}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* ── 메뉴 아이템 패널 ── */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #f0f0f0' }}>
            <span style={{ fontWeight: 600, fontSize: 15 }}>{currentCat?.name_ko ?? '전체 메뉴'}</span>
            <button className="btn-primary btn-sm" onClick={() => setEditItem(null)}>+ 메뉴 추가</button>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 56 }}></th>
                <th>이름</th>
                <th>카테고리</th>
                <th>가격</th>
                <th>품절</th>
                <th>상태</th>
                <th style={{ width: 110 }}>수정/삭제</th>
              </tr>
            </thead>
            <tbody>
              {displayItems.length === 0 && (
                <tr><td colSpan={7} className="loading-text">메뉴가 없습니다</td></tr>
              )}
              {displayItems.map(item => {
                const cat = data?.categories?.find(c => c.id === item.category_id)
                return (
                  <tr
                    key={item.id}
                    className={selectedItem === item.id ? 'selected' : ''}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setSelectedItem(selectedItem === item.id ? null : item.id)}
                  >
                    <td>
                      {item.image_url
                        ? <img src={item.image_url} alt="" style={{ width: 40, height: 40, objectFit: 'cover', borderRadius: 6 }} />
                        : <div style={{ width: 40, height: 40, background: '#f5f5f5', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>🍔</div>
                      }
                    </td>
                    <td style={{ fontWeight: 500 }}>{item.name_ko}</td>
                    <td style={{ fontSize: 12, color: '#888' }}>{cat?.name_ko ?? '–'}</td>
                    <td>{Number(item.base_price).toLocaleString('ko-KR')}원</td>
                    <td onClick={e => e.stopPropagation()}>
                      <Toggle checked={!item.is_available} onChange={() => handleToggleAvailable(item)} />
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {item.is_popular    && <span className="badge badge-active"    style={{ fontSize: 10, padding: '1px 7px' }}>인기</span>}
                        {item.is_new        && <span className="badge badge-received"  style={{ fontSize: 10, padding: '1px 7px' }}>신메뉴</span>}
                        {!item.is_available && <span className="badge badge-cancelled" style={{ fontSize: 10, padding: '1px 7px' }}>품절</span>}
                      </div>
                    </td>
                    <td onClick={e => e.stopPropagation()}>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button className="btn-outline btn-sm" onClick={() => setEditItem(item)}>수정</button>
                        <button
                          className="btn-sm"
                          style={{ background: '#ffeaea', color: '#c00', border: '1px solid #ffc0c0', borderRadius: 6, fontSize: 12, padding: '4px 8px', cursor: 'pointer' }}
                          disabled={deletingItem === item.id}
                          onClick={() => {
                            if (confirm(`"${item.name_ko}"을(를) 삭제하시겠습니까?\n진행 중인 주문이 있으면 품절 처리됩니다.`))
                              handleDeleteItem(item.id)
                          }}
                        >
                          {deletingItem === item.id ? '…' : '삭제'}
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* ── 옵션 패널 (그룹별 섹션) ── */}
        {selectedItemFull && (
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '14px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #f0f0f0' }}>
              <span style={{ fontWeight: 600, fontSize: 14 }}>{selectedItemFull.name_ko} — 옵션 구성</span>
            </div>

            {OPTION_GROUPS.map(group => (
              <OptionGroupSection
                key={group.value}
                group={group}
                options={selectedItemFull.options ?? []}
                item={selectedItemFull}
                onAdd={openAddOption}
                onEdit={openEditOption}
                onDelete={handleDeleteOption}
                onToggle={handleToggleOptionAvailable}
                deletingOpt={deletingOpt}
              />
            ))}
          </div>
        )}
      </div>

      {/* ── 모달 ── */}
      {editCat && (
        <EditCategoryModal
          category={editCat === true ? null : editCat}
          onClose={() => setEditCat(null)}
          onSave={handleSaveCat}
        />
      )}

      {editItem !== undefined && (
        <EditItemModal
          item={editItem}
          categoryId={selectedCat}
          categories={data?.categories ?? []}
          onClose={() => setEditItem(undefined)}
          onSave={handleSaveItem}
        />
      )}

      {editOption !== undefined && selectedItemFull && (
        <EditOptionModal
          option={editOption}
          itemId={selectedItemFull.id}
          defaultGroup={editOptionGroup}
          onClose={() => { setEditOption(undefined); setEditOptionGroup(null) }}
          onSave={handleSaveOption}
        />
      )}
    </div>
  )
}
