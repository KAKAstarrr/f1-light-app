import request from './request'

/**
 * 鉴权接口（模块 3A）
 */

/** 用户注册 */
export const register = (data) => {
  return request.post('/api/auth/register', data)
}

/** 用户登录 */
export const login = (data) => {
  return request.post('/api/auth/login', data)
}

/** 获取当前用户信息 */
export const getMe = () => {
  return request.get('/api/auth/me')
}
