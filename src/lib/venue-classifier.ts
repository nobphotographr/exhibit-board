// 大型ギャラリー・企業ギャラリーの判定システム

// 正規化関数（表記揺れを統一）
const normalizeVenueName = (venueName: string): string => {
  return venueName
    .replace(/\s+/g, '') // 空白除去
    .replace(/　/g, '') // 全角空白除去
    .replace(/フジフィルム/g, 'フジフイルム') // よくある間違い修正
    .replace(/富士フィルム/g, '富士フイルム') // 表記揺れ修正
    .replace(/キャノン/g, 'キヤノン') // よくある間違い修正
    .replace(/canon/gi, 'キヤノン') // Canon英語表記も統一
    .replace(/ニコン/g, 'ニコン') // 表記統一
    .toLowerCase()
}

// 大型ギャラリー・企業ギャラリーのパターン
const MAJOR_VENUES_PATTERNS = [
  // Sony/α関連
  ['αプラザ札幌', 'アルファプラザ札幌', 'α plaza 札幌'],
  ['αプラザ名古屋', 'アルファプラザ名古屋', 'α plaza 名古屋'],
  ['αプラザ大阪', 'アルファプラザ大阪', 'α plaza 大阪'],
  ['αプラザ福岡天神', 'アルファプラザ福岡天神', 'α plaza 福岡'],
  ['ソニーイメージングギャラリー銀座', 'sony imaging gallery'],

  // Fujifilm関連
  ['富士フイルムフォトサロン', '富士フィルムフォトサロン', 'フジフイルムフォトサロン', 'fujifilm photo salon'],
  ['富士フィルムフォトサロン名古屋', '富士フイルムフォトサロン名古屋', 'フジフイルムフォトサロン名古屋'],
  ['富士フィルムフォトサロン大阪', '富士フイルムフォトサロン大阪', 'フジフイルムフォトサロン大阪'],
  ['フジフイルムスクエア', 'フジフィルムスクエア', 'フジフイルム スクエア', 'fujifilm square'],
  ['富士フォトギャラリー銀座', '富士フィルムフォトギャラリー銀座'],
  ['FUJIFILM Imaging Plaza東京', 'fujifilm imaging plaza 東京', 'フジフイルムイメージングプラザ東京'],
  ['FUJIFILM Imaging Plaza大阪', 'fujifilm imaging plaza 大阪', 'フジフイルムイメージングプラザ大阪'],

  // Canon関連（「キヤノン」が含まれる会場は全て大型企画として判定）
  ['キヤノン'], // これによりキヤノンが含まれる全ての会場名をマッチ

  // Nikon関連
  ['ニコンサロン', 'nikon salon'],
  ['ニコンプラザ東京', 'nikon plaza 東京'],
  ['ニコンプラザ大阪', 'nikon plaza 大阪'],

  // Epson関連
  ['エプソンスクエア丸の内', 'epson square 丸の内'],
  ['エプサイト', 'epsite'],

  // Ricoh関連
  ['リコーイメージングスクエア東京', 'ricoh imaging square 東京'],
  ['リコーイメージングスクエア大阪', 'ricoh imaging square 大阪'],

  // OM SYSTEM関連
  ['OM SYSTEM GALLERY', 'om system gallery', 'omシステムギャラリー'],

  // その他企業ギャラリー
  ['ケンコートキナーギャラリー', 'kenko tokina gallery'],
  ['ピクトリコショップ＆ギャラリー', 'pictrico shop gallery', 'ピクトリコギャラリー'],
  ['ライカギャラリー', 'leica gallery', 'ライカギャラリー東京', 'ライカストア東京'],
  ['GR SPACE TOKYO', 'gr space tokyo', 'grスペース東京', 'grスペーストーキョー'],

  // 写真関連団体・美術館
  ['東京都写真美術館', '東京都立写真美術館', 'tokyo photographic art museum', 'top museum'],
  ['JCIIフォトサロン', 'jcii photo salon', 'jciiフォトサロン'],
]

// 大型企画の展示名・主催者パターン
const MAJOR_EXHIBITION_PATTERNS = [
  // 東京カメラ部関連
  ['東京カメラ部', 'tokyocameraclub', 'Tokyo Camera Club'],
  // その他大型写真企画
  ['CP+', 'cameraandphoto imaging show', 'シーピープラス'],
  ['写真の日', 'フォトの日'],
  ['世界報道写真展', 'world press photo'],
]

/**
 * 会場が大型ギャラリー・企業ギャラリーかどうかを判定
 * @param venueName 会場名
 * @returns true: 大型ギャラリー, false: 個展・グループ展
 */
export const isMajorVenue = (venueName: string): boolean => {
  if (!venueName) return false
  
  const normalized = normalizeVenueName(venueName)
  
  return MAJOR_VENUES_PATTERNS.some(patterns => 
    patterns.some(pattern => {
      const normalizedPattern = normalizeVenueName(pattern)
      return normalized.includes(normalizedPattern) || normalizedPattern.includes(normalized)
    })
  )
}

/**
 * 展示名・主催者から大型企画かどうかを判定
 * @param title 展示タイトル
 * @param hostName 主催者名
 * @returns true: 大型企画, false: 個展・グループ展
 */
export const isMajorExhibition = (title?: string, hostName?: string): boolean => {
  const textToCheck = `${title || ''} ${hostName || ''}`
  if (!textToCheck.trim()) return false
  
  const normalized = normalizeVenueName(textToCheck)
  
  return MAJOR_EXHIBITION_PATTERNS.some(patterns => 
    patterns.some(pattern => {
      const normalizedPattern = normalizeVenueName(pattern)
      return normalized.includes(normalizedPattern) || normalizedPattern.includes(normalized)
    })
  )
}

/**
 * 総合判定：会場名と展示名の両方をチェック
 * @param venueName 会場名
 * @param title 展示タイトル
 * @param hostName 主催者名
 * @returns true: 大型企画, false: 個展・グループ展
 */
export const isMajorEvent = (venueName: string, title?: string, hostName?: string): boolean => {
  return isMajorVenue(venueName) || isMajorExhibition(title, hostName)
}

/**
 * 会場タイプを取得
 * @param venueName 会場名  
 * @param title 展示タイトル
 * @param hostName 主催者名
 * @returns 'major' | 'independent'
 */
export const getVenueType = (venueName: string, title?: string, hostName?: string): 'major' | 'independent' => {
  return isMajorEvent(venueName, title, hostName) ? 'major' : 'independent'
}

/**
 * デバッグ用：判定結果を詳細表示
 * @param venueName 会場名
 */
export const debugVenueClassification = (venueName: string) => {
  const normalized = normalizeVenueName(venueName)
  const isMajor = isMajorVenue(venueName)
  
  console.log({
    original: venueName,
    normalized,
    classification: isMajor ? 'major' : 'independent',
    isMajor
  })
}