import bcrypt from 'bcryptjs'

const ROUNDS = 12

export function hashPassword(plain: string): string {
  return bcrypt.hashSync(plain, ROUNDS)
}

export function verifyPassword(plain: string, hash: string): boolean {
  return bcrypt.compareSync(plain, hash)
}
