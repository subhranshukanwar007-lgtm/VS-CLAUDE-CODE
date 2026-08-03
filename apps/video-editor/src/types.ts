export interface Clip {
  id: string
  file: File
  url: string
  name: string
  duration: number
  /** Trim start, in seconds, relative to the original file */
  trimStart: number
  /** Trim end, in seconds, relative to the original file */
  trimEnd: number
  muted: boolean
  speed: number
  text: string
  textPosition: 'top' | 'middle' | 'bottom'
}
