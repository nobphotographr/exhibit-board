interface RecaptchaResponse {
  success: boolean
  score?: number
  action?: string
  challenge_ts?: string
  hostname?: string
  'error-codes'?: string[]
}

export async function verifyRecaptcha(token: string): Promise<{ 
  success: boolean 
  score: number 
  error?: string 
}> {
  const secretKey = process.env.RECAPTCHA_SECRET
  
  if (!secretKey) {
    console.error('RECAPTCHA_SECRET environment variable is not set')
    return { success: false, score: 0, error: 'reCAPTCHA not configured' }
  }

  try {
    const response = await fetch('https://www.google.com/recaptcha/api/siteverify', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        secret: secretKey,
        response: token,
      }),
    })

    const data: RecaptchaResponse = await response.json()

    if (!data.success) {
      console.error('reCAPTCHA verification failed:', data['error-codes'])
      return { 
        success: false, 
        score: 0, 
        error: `reCAPTCHA verification failed: ${data['error-codes']?.join(', ') || 'Unknown error'}` 
      }
    }

    // reCAPTCHA v3 provides a score between 0.0 and 1.0
    // Higher score means more likely to be human
    const score = data.score ?? 0

    return { success: true, score }

  } catch (error) {
    console.error('Error verifying reCAPTCHA:', error)
    return { 
      success: false, 
      score: 0, 
      error: 'Failed to verify reCAPTCHA' 
    }
  }
}

export function shouldMarkAsPending(score: number, threshold = 0.5): boolean {
  // If score is below threshold, mark as pending for review
  return score < threshold
}

export function isScoreAcceptable(score: number, minThreshold = 0.1): boolean {
  // Very low scores (likely bots) should be rejected entirely
  return score >= minThreshold
}