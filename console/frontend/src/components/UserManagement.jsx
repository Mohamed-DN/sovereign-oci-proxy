import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  Users,
  UserPlus,
  Shield,
  Zap,
  HardDrive,
  Activity,
  Key,
  Trash2,
  Lock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Plus,
  X
} from 'lucide-react';

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [isProvisionModalOpen, setIsProvisionModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  // Form State
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('user');
  const [tier, setTier] = useState('hybrid_byos');
  const [bandwidthQuota, setBandwidthQuota] = useState(500);
  const [maxNodes, setMaxNodes] = useState(5);

  const loadUsers = async () => {
    try {
      const list = await api.users.list();
      setUsers(list);
    } catch (err) {
      console.error('Failed to load users:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      await api.users.create({
        username,
        email,
        role,
        tier,
        bandwidth_quota_gb: bandwidthQuota,
        max_nodes: maxNodes
      });
      setIsProvisionModalOpen(false);
      setUsername('');
      setEmail('');
      loadUsers();
    } catch (err) {
      console.error('Failed to create user:', err);
    }
  };

  const handleRevokeSessions = async (userId) => {
    if (window.confirm('Revoke all active JWT sessions and refresh tokens for this user?')) {
      await api.users.revokeSessions(userId);
      alert('All active user sessions revoked.');
    }
  };

  const handleDeleteUser = async (userId) => {
    if (window.confirm('Are you sure you want to delete this user and disconnect all their devices?')) {
      await api.users.delete(userId);
      loadUsers();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
            <span>Dual-Tier User Directory & Quotas</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/40">
              {users.length} Active Tenants
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Enterprise RBAC managing Hybrid BYOS ($0 self-hosted) vs Managed Cloud ($12/mo) tenancy.
          </p>
        </div>

        <button
          onClick={() => setIsProvisionModalOpen(true)}
          className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-gradient-to-r from-neon-cyan to-neon-indigo text-dark-canvas font-bold font-mono text-xs hover:brightness-110 transition-all shadow-lg"
        >
          <UserPlus className="w-4 h-4" />
          <span>Provision User</span>
        </button>
      </div>

      {/* Tier Breakdown Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 rounded-2xl bg-dark-card border border-neon-emerald/30 space-y-2 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-neon-emerald/20 text-neon-emerald border border-neon-emerald/40">
              HYBRID BYOS TIER ($0 / Mo)
            </span>
            <HardDrive className="w-5 h-5 text-neon-emerald" />
          </div>
          <div className="text-sm font-bold text-slate-100 font-mono">Self-Hosted Sovereign Storage</div>
          <p className="text-xs text-slate-400">
            User hosts their own hardware (TrueNAS, Synology, Raspberry Pi). Zero server storage liability for NeroNet, full mesh routing.
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-dark-card border border-neon-cyan/30 space-y-2 relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/40">
              MANAGED CLOUD TIER ($12 / Mo)
            </span>
            <Zap className="w-5 h-5 text-neon-cyan" />
          </div>
          <div className="text-sm font-bold text-slate-100 font-mono">Zero-Knowledge Encrypted Cloud</div>
          <p className="text-xs text-slate-400">
            Dedicated multi-region cloud containers on OCI/AWS with provisioned bandwidth and client-side encryption.
          </p>
        </div>
      </div>

      {/* User Directory Table */}
      <div className="rounded-xl bg-dark-card border border-dark-border overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-dark-canvas text-slate-400 uppercase text-[10px] tracking-wider border-b border-dark-border">
              <tr>
                <th className="p-3.5">User Identity</th>
                <th className="p-3.5">Role</th>
                <th className="p-3.5">Hosting Tier</th>
                <th className="p-3.5">Bandwidth Quota (Used / Total)</th>
                <th className="p-3.5">Max Nodes</th>
                <th className="p-3.5">Account Status</th>
                <th className="p-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-border">
              {users.map((u) => {
                const usedGb = +(u.bandwidth_used_bytes / 1024 / 1024 / 1024).toFixed(1);
                const totalGb = u.bandwidth_quota_gb || 500;
                const pct = Math.min(100, Math.round((usedGb / totalGb) * 100));

                return (
                  <tr key={u.id} className="hover:bg-dark-card-hover transition-colors">
                    {/* User Identity */}
                    <td className="p-3.5">
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center font-bold text-white text-xs">
                          {u.username[0].toUpperCase()}
                        </div>
                        <div>
                          <div className="font-bold text-slate-100">{u.username}</div>
                          <div className="text-[10px] text-slate-500">{u.email}</div>
                        </div>
                      </div>
                    </td>

                    {/* Role */}
                    <td className="p-3.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        u.role === 'super-admin'
                          ? 'bg-neon-indigo/20 text-neon-indigo border border-neon-indigo/40'
                          : 'bg-dark-canvas text-slate-400 border border-dark-border'
                      }`}>
                        {u.role}
                      </span>
                    </td>

                    {/* Tier */}
                    <td className="p-3.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        u.tier === 'cloud_managed'
                          ? 'bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/40'
                          : 'bg-neon-emerald/20 text-neon-emerald border border-neon-emerald/40'
                      }`}>
                        {u.tier === 'cloud_managed' ? 'Cloud Managed ($12/mo)' : 'Hybrid BYOS ($0)'}
                      </span>
                    </td>

                    {/* Quota Gauge */}
                    <td className="p-3.5 min-w-[160px]">
                      <div className="space-y-1">
                        <div className="flex justify-between text-[11px]">
                          <span className="text-slate-300 font-bold">{usedGb} GB</span>
                          <span className="text-slate-500">/ {totalGb} GB</span>
                        </div>
                        <div className="w-full bg-dark-canvas rounded-full h-1.5 overflow-hidden border border-dark-border">
                          <div
                            className={`h-full ${pct > 90 ? 'bg-neon-rose' : 'bg-neon-cyan'}`}
                            style={{ width: `${pct}%` }}
                          ></div>
                        </div>
                      </div>
                    </td>

                    {/* Max Nodes */}
                    <td className="p-3.5 text-slate-300 font-bold">
                      {u.max_nodes || 5} Devices
                    </td>

                    {/* Status */}
                    <td className="p-3.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        u.status === 'active'
                          ? 'bg-neon-emerald/20 text-neon-emerald'
                          : 'bg-neon-rose/20 text-neon-rose'
                      }`}>
                        {u.status?.toUpperCase()}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="p-3.5 text-right space-x-2">
                      <button
                        onClick={() => handleRevokeSessions(u.id)}
                        className="px-2.5 py-1 rounded bg-dark-canvas border border-dark-border text-slate-400 hover:text-neon-amber text-xs transition-colors"
                        title="Revoke Sessions"
                      >
                        Revoke Tokens
                      </button>
                      <button
                        onClick={() => handleDeleteUser(u.id)}
                        className="p-1.5 rounded bg-dark-canvas border border-dark-border text-slate-400 hover:text-neon-rose text-xs transition-colors"
                        title="Delete User"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Provision User Modal */}
      {isProvisionModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-dark-card border border-dark-border rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl">
            <div className="p-5 border-b border-dark-border flex items-center justify-between bg-dark-canvas">
              <div className="flex items-center space-x-2 font-bold text-slate-100 font-mono">
                <UserPlus className="w-4 h-4 text-neon-cyan" />
                <span>Provision New Mesh Tenant</span>
              </div>
              <button
                onClick={() => setIsProvisionModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="p-6 space-y-4 text-xs font-mono">
              <div>
                <label className="block text-slate-400 mb-1">Username</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. eve_ops"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded-lg text-slate-100 focus:outline-none focus:border-neon-cyan"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  placeholder="e.g. eve@darknero.net"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded-lg text-slate-100 focus:outline-none focus:border-neon-cyan"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Role</label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded-lg text-slate-100 focus:outline-none focus:border-neon-cyan"
                  >
                    <option value="user">Standard User</option>
                    <option value="super-admin">Super-Admin</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Hosting Tier</label>
                  <select
                    value={tier}
                    onChange={(e) => setTier(e.target.value)}
                    className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded-lg text-slate-100 focus:outline-none focus:border-neon-cyan"
                  >
                    <option value="hybrid_byos">Hybrid BYOS ($0)</option>
                    <option value="cloud_managed">Cloud Managed ($12/mo)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Bandwidth Quota (GB)</label>
                  <input
                    type="number"
                    value={bandwidthQuota}
                    onChange={(e) => setBandwidthQuota(e.target.value)}
                    className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded-lg text-slate-100 focus:outline-none focus:border-neon-cyan"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Max Devices</label>
                  <input
                    type="number"
                    value={maxNodes}
                    onChange={(e) => setMaxNodes(e.target.value)}
                    className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded-lg text-slate-100 focus:outline-none focus:border-neon-cyan"
                  />
                </div>
              </div>

              <div className="pt-4 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setIsProvisionModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-dark-border text-slate-300 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-gradient-to-r from-neon-cyan to-neon-indigo text-dark-canvas font-bold hover:brightness-110"
                >
                  Create Tenant
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
