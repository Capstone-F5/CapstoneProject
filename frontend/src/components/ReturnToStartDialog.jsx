import Logo from './Logo'

export default function ReturnToStartDialog({ onConfirm, onCancel }) {
  return (
    <div
      onClick={onCancel}
      style={{
        position: 'fixed', inset: 0, zIndex: 200,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '0 clamp(20px, 6vw, 32px)',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#fff',
          borderRadius: 20,
          width: '92%',
          maxWidth: 520,
          overflow: 'hidden',
          boxShadow: '0 8px 40px rgba(0,0,0,0.25)',
        }}
      >
        {/* Content */}
        <div style={{
          padding: 'clamp(28px, 8vw, 40px) clamp(20px, 6vw, 32px) clamp(24px, 7vw, 36px)',
          display: 'flex', flexDirection: 'column', alignItems: 'center',
        }}>
          <div style={{ marginBottom: 20 }}>
            <Logo height={36} />
          </div>

          <div style={{
            fontSize: 'clamp(16px, 5vw, 20px)', fontWeight: 700,
            color: '#1a1a1a', textAlign: 'center',
          }}>
            첫 화면으로 돌아가시겠습니까?
          </div>
        </div>

        {/* Buttons */}
        <div style={{ display: 'flex', borderTop: '1px solid #eee' }}>
          <button
            onClick={onConfirm}
            style={{
              flex: 1, padding: 'clamp(16px, 5vw, 20px) 0',
              border: 'none', background: '#f0f0f0',
              fontSize: 'clamp(15px, 4.5vw, 18px)', fontWeight: 700,
              color: '#555', cursor: 'pointer',
              borderRight: '1px solid #eee',
            }}
          >
            예
          </button>
          <button
            onClick={onCancel}
            style={{
              flex: 1, padding: 'clamp(16px, 5vw, 20px) 0',
              border: 'none', background: '#744032',
              fontSize: 'clamp(15px, 4.5vw, 18px)', fontWeight: 700,
              color: '#fff', cursor: 'pointer',
            }}
          >
            아니요
          </button>
        </div>
      </div>
    </div>
  )
}
