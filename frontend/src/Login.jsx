import { useState } from 'react';

import API from './config';

export default function Login({ onLogin }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        // Prepare form data for OAuth2 format
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        // API URL (Dynamic from config.js)
        const API_URL = API.LOGIN;

        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Invalid credentials');
            }

            const data = await response.json();
            onLogin(data.access_token);
        } catch (err) {
            setError('Login failed: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-slate-900">
            <div className="bg-slate-800 p-8 rounded-xl shadow-2xl border border-slate-700 w-96">
                <h2 className="text-2xl font-bold text-white mb-6 text-center">RecoverAI Login</h2>

                {error && (
                    <div className="bg-red-500/20 text-red-400 p-3 rounded mb-4 text-sm text-center">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-slate-400 text-sm mb-1">Username</label>
                        <input
                            type="text"
                            className="w-full bg-slate-700 text-white rounded p-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="admin"
                        />
                    </div>
                    <div>
                        <label className="block text-slate-400 text-sm mb-1">Password</label>
                        <input
                            type="password"
                            className="w-full bg-slate-700 text-white rounded p-2 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="password"
                        />
                    </div>
                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-emerald-500 hover:bg-emerald-600 text-white font-bold py-2 px-4 rounded transition-colors disabled:opacity-50"
                    >
                        {loading ? 'Verifying...' : 'Sign In'}
                    </button>
                </form>

                <div className="mt-4 text-center text-xs text-slate-500">
                    MVP Default: admin / password123
                </div>
            </div>
        </div>
    );
}
