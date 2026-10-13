/** 원문 순서를 보존하면서 숫자와 단위만 강조한다. */
export function NumericFact({ text }: { text: string }) {
  const parts = text.split(
    /([+−-]?\d[\d,.]*(?:\s*(?:%|조|억|만|천|달러|원|배|bp|명|년|개월|일|시간|분|개|건|포인트))?)/g,
  )
  return (
    <p className="numeric-fact">
      {parts.map((part, i) =>
        i % 2 ? <strong key={i}>{part}</strong> : <span key={i}>{part}</span>,
      )}
    </p>
  )
}
