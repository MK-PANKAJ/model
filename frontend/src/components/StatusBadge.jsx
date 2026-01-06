export default function StatusBadge({ status }) {
    const getStatusStyle = (status) => {
        const styles = {
            'PENDING': {
                bg: 'bg-gray-100',
                text: 'text-gray-700',
                border: 'border-gray-300',
                icon: '⏳'
            },
            'IN_PROGRESS': {
                bg: 'bg-blue-100',
                text: 'text-blue-700',
                border: 'border-blue-300',
                icon: '🔄'
            },
            'UNDER_REVIEW': {
                bg: 'bg-yellow-100',
                text: 'text-yellow-700',
                border: 'border-yellow-300',
                icon: '👁'
            },
            'RESOLVED': {
                bg: 'bg-green-100',
                text: 'text-green-700',
                border: 'border-green-300',
                icon: '✓'
            },
            'CLOSED': {
                bg: 'bg-slate-100',
                text: 'text-slate-700',
                border: 'border-slate-300',
                icon: '🔒'
            },
            'ESCALATED': {
                bg: 'bg-red-100',
                text: 'text-red-700',
                border: 'border-red-300',
                icon: '⚠'
            }
        };

        return styles[status] || styles['PENDING'];
    };

    const style = getStatusStyle(status);

    return (
        <span
            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${style.bg} ${style.text} ${style.border}`}
        >
            <span>{style.icon}</span>
            <span>{status.replace('_', ' ')}</span>
        </span>
    );
}
