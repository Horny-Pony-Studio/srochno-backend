# 🔗 Frontend Integration Guide

Complete guide for integrating the Next.js frontend with this FastAPI backend.

## Quick Start

### 1. Update Frontend Environment

In `/home/pony/srochno/.env.local`:

```env
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000/api

# For production
# NEXT_PUBLIC_API_URL=https://api.srochno.ru/api
```

### 2. Create API Client

Create `/home/pony/srochno/src/lib/api.ts`:

```typescript
// API Client with Telegram authentication
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// Get Telegram initData for authentication
function getInitData(): string {
  if (typeof window !== 'undefined' && window.Telegram?.WebApp) {
    return window.Telegram.WebApp.initData;
  }
  // Development fallback (mock data)
  if (process.env.NODE_ENV === 'development') {
    return 'mock_init_data_for_development';
  }
  throw new Error('Telegram WebApp not available');
}

// Authenticated fetch wrapper
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const initData = getInitData();

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${initData}`,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'API request failed');
  }

  return response.json();
}

// Public fetch (no auth)
async function publicFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'API request failed');
  }

  return response.json();
}

export const api = {
  // Orders (public browsing)
  listOrders: (params?: {
    category?: string;
    city?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) => {
    const query = new URLSearchParams(
      Object.entries(params || {}).filter(([_, v]) => v != null) as [string, string][]
    );
    return publicFetch<OrderListResponse>(`/orders?${query}`);
  },

  // Orders (authenticated)
  getOrder: (id: string) =>
    apiFetch<OrderDetailResponse>(`/orders/${id}`),

  createOrder: (data: CreateOrderRequest) =>
    apiFetch<OrderResponse>('/orders', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateOrder: (id: string, data: UpdateOrderRequest) =>
    apiFetch<OrderResponse>(`/orders/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteOrder: (id: string) =>
    apiFetch<void>(`/orders/${id}`, { method: 'DELETE' }),

  takeOrder: (id: string) =>
    apiFetch<ExecutorTakeResponse>(`/orders/${id}/take`, {
      method: 'POST',
    }),

  // User
  getProfile: () =>
    apiFetch<UserProfileResponse>('/users/me'),

  updatePreferences: (data: { categories: string[]; cities: string[] }) =>
    apiFetch<{ success: boolean }>('/users/me/preferences', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  updateNotificationSettings: (frequency: number) =>
    apiFetch<{ success: boolean }>('/users/me/notification-settings', {
      method: 'PUT',
      body: JSON.stringify({ frequency }),
    }),

  // Balance
  getBalance: () =>
    apiFetch<BalanceResponse>('/balance'),

  rechargeBalance: (amount: number, method: string = 'telegram_stars') =>
    apiFetch<RechargeResponse>('/balance/recharge', {
      method: 'POST',
      body: JSON.stringify({ amount, method }),
    }),

  // Reviews
  createClientReview: (data: ClientReviewRequest) =>
    apiFetch<ClientReviewResponse>('/reviews/client', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  createExecutorComplaint: (data: ExecutorComplaintRequest) =>
    apiFetch<{ success: boolean; complaint_id: number }>('/reviews/executor', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  listReviews: (rating?: number) => {
    const query = rating ? `?rating=${rating}` : '';
    return publicFetch<ReviewResponse[]>(`/reviews${query}`);
  },
};

// TypeScript types (match backend schemas)
export interface CreateOrderRequest {
  category: string;
  description: string;
  city: string;
  contact: string;
}

export interface UpdateOrderRequest {
  category?: string;
  description?: string;
  contact?: string;
}

export interface OrderResponse {
  id: string;
  category: string;
  description: string;
  city: string;
  contact: string | null;
  created_at: string;
  expires_in_minutes: number;
  status: 'active' | 'expired' | 'deleted' | 'closed_no_response' | 'completed';
  taken_by: { executor_id: number; taken_at: string }[];
  customer_response: string | null;
  city_locked: boolean;
}

export interface OrderListResponse {
  orders: OrderResponse[];
  total: number;
}

export interface OrderDetailResponse extends OrderResponse {
  contact: string; // Always visible after payment
}

export interface ExecutorTakeResponse {
  success: boolean;
  contact: string;
  executor_count: number;
  new_balance: number;
}

export interface UserProfileResponse {
  id: number;
  first_name: string;
  last_name: string | null;
  username: string | null;
  completed_orders: number;
  active_orders: number;
  rating: number;
  balance: number;
}

export interface BalanceResponse {
  balance: number;
}

export interface RechargeResponse {
  success: boolean;
  new_balance: number;
  transaction_id: number;
}

export interface ClientReviewRequest {
  order_id: string;
  rating: number;
  comment?: string;
}

export interface ClientReviewResponse {
  success: boolean;
  review_id: number;
}

export interface ExecutorComplaintRequest {
  order_id: string;
  complaint: string;
  comment?: string;
}

export interface ReviewResponse {
  id: number;
  author_name: string;
  rating: number;
  comment: string | null;
  category: string;
  created_at: string;
}
```

## Usage Examples

### Example 1: Create Order Page

Update `/home/pony/srochno/app/create-order/page.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { useHaptic } from '@/hooks/useTelegram';

export default function CreateOrderPage() {
  const router = useRouter();
  const haptic = useHaptic();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: {
    category: string;
    description: string;
    city: string;
    contact: string;
  }) => {
    try {
      setLoading(true);
      setError(null);

      const order = await api.createOrder(data);

      haptic.notification('success');
      router.push(`/customer`);
    } catch (err) {
      haptic.notification('error');
      setError(err instanceof Error ? err.message : 'Failed to create order');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Form fields */}
      {error && <div className="error">{error}</div>}
      <button type="submit" disabled={loading}>
        {loading ? 'Creating...' : 'Create Order'}
      </button>
    </form>
  );
}
```

### Example 2: Orders List Page

Update `/home/pony/srochno/app/orders/page.tsx`:

```typescript
'use client';

import { useEffect, useState } from 'react';
import { api, OrderResponse } from '@/lib/api';
import { OrderCard } from '@/components/OrderCard';

export default function OrdersPage() {
  const [orders, setOrders] = useState<OrderResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState<string | undefined>();
  const [city, setCity] = useState<string | undefined>();

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        const response = await api.listOrders({ category, city });
        setOrders(response.orders);
      } catch (error) {
        console.error('Failed to fetch orders:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchOrders();

    // Refresh every 10 seconds
    const interval = setInterval(fetchOrders, 10000);
    return () => clearInterval(interval);
  }, [category, city]);

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      {/* Filters */}
      <select onChange={(e) => setCategory(e.target.value || undefined)}>
        <option value="">All Categories</option>
        <option value="Сантехника">Сантехника</option>
        {/* ... */}
      </select>

      {/* Order list */}
      {orders.map((order) => (
        <OrderCard key={order.id} order={order} />
      ))}
    </div>
  );
}
```

### Example 3: Take Order (Executor)

Update `/home/pony/srochno/app/orders/[id]/page.tsx`:

```typescript
'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { useHaptic } from '@/hooks/useTelegram';

export default function OrderDetailPage({ params }: { params: { id: string } }) {
  const [contact, setContact] = useState<string | null>(null);
  const [balance, setBalance] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const haptic = useHaptic();

  const handleTakeOrder = async () => {
    try {
      setLoading(true);

      const response = await api.takeOrder(params.id);

      setContact(response.contact);
      setBalance(response.new_balance);

      haptic.notification('success');
      alert(`Contact: ${response.contact}\nYour balance: ${response.new_balance}₽`);
    } catch (err) {
      haptic.notification('error');
      alert(err instanceof Error ? err.message : 'Failed to take order');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* Order details */}

      {contact ? (
        <div>
          <strong>Contact:</strong> {contact}
        </div>
      ) : (
        <button onClick={handleTakeOrder} disabled={loading}>
          {loading ? 'Processing...' : 'Take Order (2₽)'}
        </button>
      )}

      {balance !== null && <div>Balance: {balance}₽</div>}
    </div>
  );
}
```

### Example 4: Profile Page with Balance

Update `/home/pony/srochno/app/profile/page.tsx`:

```typescript
'use client';

import { useEffect, useState } from 'react';
import { api, UserProfileResponse } from '@/lib/api';

export default function ProfilePage() {
  const [profile, setProfile] = useState<UserProfileResponse | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const data = await api.getProfile();
        setProfile(data);
      } catch (error) {
        console.error('Failed to fetch profile:', error);
      }
    };

    fetchProfile();
  }, []);

  const handleRecharge = async (amount: number) => {
    try {
      const response = await api.rechargeBalance(amount);
      setProfile((prev) => prev ? { ...prev, balance: response.new_balance } : null);
      alert(`Balance recharged! New balance: ${response.new_balance}₽`);
    } catch (error) {
      alert('Recharge failed');
    }
  };

  if (!profile) return <div>Loading...</div>;

  return (
    <div>
      <h1>{profile.first_name} {profile.last_name}</h1>
      <p>@{profile.username}</p>
      <p>Balance: {profile.balance}₽</p>
      <p>Rating: {profile.rating.toFixed(1)} ⭐</p>
      <p>Completed: {profile.completed_orders}</p>

      <div>
        <button onClick={() => handleRecharge(100)}>+ 100₽</button>
        <button onClick={() => handleRecharge(300)}>+ 300₽</button>
        <button onClick={() => handleRecharge(1000)}>+ 1000₽</button>
      </div>
    </div>
  );
}
```

### Example 5: Leave Review

```typescript
'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

export default function LeaveReviewPage({ orderId }: { orderId: string }) {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState('');

  const handleSubmit = async () => {
    try {
      await api.createClientReview({
        order_id: orderId,
        rating,
        comment: comment || undefined,
      });
      alert('Review submitted!');
    } catch (error) {
      alert('Failed to submit review');
    }
  };

  return (
    <div>
      <h2>Rate Executor</h2>
      <input
        type="range"
        min="1"
        max="5"
        value={rating}
        onChange={(e) => setRating(Number(e.target.value))}
      />
      <div>{rating} ⭐</div>

      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Optional comment (max 500 chars)"
        maxLength={500}
      />

      <button onClick={handleSubmit}>Submit Review</button>
    </div>
  );
}
```

## Error Handling

### Common Errors

```typescript
try {
  await api.takeOrder(orderId);
} catch (error) {
  if (error.message.includes('Insufficient balance')) {
    // Show recharge dialog
    showRechargeDialog();
  } else if (error.message.includes('Maximum 3 executors')) {
    // Order at capacity
    alert('Order already has 3 executors');
  } else if (error.message.includes('expired')) {
    // Order expired
    router.push('/orders');
  } else {
    // Generic error
    alert('Something went wrong');
  }
}
```

### Error Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 401 | Invalid Telegram auth | Refresh page |
| 402 | Insufficient balance | Show recharge dialog |
| 403 | Cannot edit order | Disable edit button |
| 404 | Order not found | Redirect to list |
| 409 | Max executors | Disable take button |
| 410 | Order expired | Show expired state |
| 422 | Validation error | Show field errors |

## React Query Integration (Recommended)

Install React Query (already in package.json):

```bash
npm install @tanstack/react-query
```

Create `/home/pony/srochno/src/lib/queries.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from './api';

// Orders
export function useOrders(filters?: { category?: string; city?: string }) {
  return useQuery({
    queryKey: ['orders', filters],
    queryFn: () => api.listOrders(filters),
    refetchInterval: 10000, // Auto-refresh every 10s
  });
}

export function useOrder(id: string) {
  return useQuery({
    queryKey: ['order', id],
    queryFn: () => api.getOrder(id),
  });
}

export function useCreateOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: api.createOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}

export function useTakeOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (orderId: string) => api.takeOrder(orderId),
    onSuccess: (_, orderId) => {
      queryClient.invalidateQueries({ queryKey: ['order', orderId] });
      queryClient.invalidateQueries({ queryKey: ['profile'] });
    },
  });
}

// User
export function useProfile() {
  return useQuery({
    queryKey: ['profile'],
    queryFn: api.getProfile,
  });
}

export function useRechargeBalance() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (amount: number) => api.rechargeBalance(amount),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] });
    },
  });
}
```

Usage with React Query:

```typescript
'use client';

import { useOrders, useTakeOrder } from '@/lib/queries';

export default function OrdersPage() {
  const { data, isLoading, error } = useOrders({ category: 'Сантехника' });
  const takeOrder = useTakeOrder();

  const handleTake = async (orderId: string) => {
    try {
      const result = await takeOrder.mutateAsync(orderId);
      alert(`Contact: ${result.contact}`);
    } catch (error) {
      alert(error.message);
    }
  };

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {data?.orders.map((order) => (
        <div key={order.id}>
          <h3>{order.category}</h3>
          <button onClick={() => handleTake(order.id)}>
            Take Order (2₽)
          </button>
        </div>
      ))}
    </div>
  );
}
```

## Development Tips

### 1. Mock Auth for Development

When testing without Telegram:

```typescript
// In api.ts
function getInitData(): string {
  if (process.env.NODE_ENV === 'development') {
    // Generate mock initData for local testing
    // IMPORTANT: Backend must have same bot token
    return 'user=%7B%22id%22%3A123456789%2C%22first_name%22%3A%22Test%22%2C%22username%22%3A%22testuser%22%7D&hash=mock_hash';
  }
  return window.Telegram.WebApp.initData;
}
```

### 2. Backend CORS Configuration

Backend already configured for `http://localhost:10002`.

For production, update backend `.env`:
```env
CORS_ORIGINS=https://your-telegram-webapp.com
```

### 3. Timer Sync

Frontend timer should sync with server:

```typescript
function useOrderTimer(order: OrderResponse) {
  const [minutesLeft, setMinutesLeft] = useState(0);

  useEffect(() => {
    const calculateRemaining = () => {
      const now = Date.now();
      const createdAt = new Date(order.created_at).getTime();
      const expiresAt = createdAt + order.expires_in_minutes * 60 * 1000;
      const remaining = Math.max(0, Math.floor((expiresAt - now) / 60000));
      setMinutesLeft(remaining);
    };

    calculateRemaining();
    const interval = setInterval(calculateRemaining, 1000);
    return () => clearInterval(interval);
  }, [order]);

  return minutesLeft;
}
```

### 4. Optimistic Updates

For better UX:

```typescript
const createOrder = useMutation({
  mutationFn: api.createOrder,
  onMutate: async (newOrder) => {
    // Cancel outgoing queries
    await queryClient.cancelQueries({ queryKey: ['orders'] });

    // Snapshot current value
    const previous = queryClient.getQueryData(['orders']);

    // Optimistically update
    queryClient.setQueryData(['orders'], (old: any) => ({
      ...old,
      orders: [...old.orders, { ...newOrder, id: 'temp', status: 'active' }],
    }));

    return { previous };
  },
  onError: (err, newOrder, context) => {
    // Rollback on error
    queryClient.setQueryData(['orders'], context.previous);
  },
  onSettled: () => {
    // Refetch after success or error
    queryClient.invalidateQueries({ queryKey: ['orders'] });
  },
});
```

## Testing

### Unit Tests

```typescript
// __tests__/api.test.ts
import { api } from '@/lib/api';

jest.mock('global', () => ({
  fetch: jest.fn(),
}));

describe('API Client', () => {
  it('should create order', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => ({ id: '123', status: 'active' }),
    });

    const order = await api.createOrder({
      category: 'Сантехника',
      description: 'Test order description that is long enough',
      city: 'Москва',
      contact: '@testuser',
    });

    expect(order.id).toBe('123');
  });
});
```

## Troubleshooting

### "Invalid Telegram initData"

**Problem**: Backend rejects authentication

**Solutions**:
1. Check `TELEGRAM_BOT_TOKEN` matches in backend `.env`
2. Ensure frontend sends raw `initData` string
3. Verify initData hasn't expired (>1 hour old)

```typescript
// Debug initData
console.log('initData:', window.Telegram.WebApp.initData);
console.log('initDataUnsafe:', window.Telegram.WebApp.initDataUnsafe);
```

### "CORS Error"

**Problem**: Browser blocks request

**Solutions**:
1. Check backend `CORS_ORIGINS` includes frontend URL
2. Ensure backend running on correct port
3. Use same protocol (both http or both https)

### "Order expired" but timer shows time left

**Problem**: Client/server time mismatch

**Solution**: Always trust server time
```typescript
// Fetch order to get server-calculated time
const order = await api.getOrder(orderId);
// Use order.created_at for calculations
```

