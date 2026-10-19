// 首页四个预置场景，点一下直接把表单填好，省得每次现敲

import type { InputPayload } from './types'

export interface PresetScenario extends InputPayload {
  id: string
  label: string
  hint: string
}

export const PRESETS: PresetScenario[] = [
  {
    id: 'quake',
    label: '山区地震',
    hint: '老旧建筑 + 余震',
    scene:
      '凌晨3点，山区县城发生6.2级地震，震中在城东的老城区，多处砖混结构房屋倒塌，有居民被埋压，部分道路出现裂缝，电力与通信一度中断，震后已记录到多次余震。',
    disasterType: '地震',
    severity: '严重',
    location: '西部山区县城老城区',
    timeHint: '今日凌晨 03:00',
  },
  {
    id: 'flood',
    label: '流域洪涝',
    hint: '堤防险情 + 转移',
    scene:
      '连续两天暴雨，河道水位超过警戒线，下游低洼村庄进水，部分堤段出现渗漏险情，农田被淹，约两千名群众需要转移安置。',
    disasterType: '洪涝',
    severity: '严重',
    location: '某江中下游沿河乡镇',
    timeHint: '近 48 小时',
  },
  {
    id: 'fire',
    label: '山林火灾',
    hint: '大风 + 靠近居民点',
    scene:
      '连续高温干旱，林场突发山火，受大风影响火线快速向东蔓延，已逼近山脚居民点，浓烟较大，扑救队伍正在开设隔离带。',
    disasterType: '山火',
    severity: '一般',
    location: '南部林场东侧山脊',
    timeHint: '今日下午',
  },
  {
    id: 'chem',
    label: '化工泄漏',
    hint: '有毒气体扩散',
    scene:
      '厂区储罐区发生化学品泄漏，现场有刺激性气味，风向为东南风，下风向一公里内有居民小区，已有工人出现不适，需要紧急疏散和处置。',
    disasterType: '化工泄漏',
    severity: '特重',
    location: '某化工园区储罐区',
    timeHint: '刚刚发生',
  },
]
