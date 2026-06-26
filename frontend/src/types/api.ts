import type { components } from '@/lib/api/schema'

type Schemas = components['schemas']

export type User = Schemas['UserRead']
export type UserCreate = Schemas['UserCreate']
export type UserUpdate = Schemas['UserUpdate']
export type ErrorModel = Schemas['ErrorModel']
