import { useRef, useState } from 'react'
import { uploadSurveyCsv } from '../../api/client'

export default function CsvUpload({ resultId, onUploaded }) {
    const inputRef = useRef(null)

    const [file, setFile] = useState(null)
    const [loading, setLoading] = useState(false)
    const [message, setMessage] = useState('')

    function openFilePicker() {
        inputRef.current?.click()
    }

    async function handleFileChange(e) {
        const selectFile = e.target.files[0]

        if (!selectFile) {
            setFile(null)
            return
        }

        const isCsv = selectFile.type === 'text/csv' || selectFile.name.toLowerCase().endsWith('.csv')

        if (!isCsv) {
            setFile(null)
            setMessage('CSV 파일만 업로드할 수 있습니다.')
            return
        }

        setFile(selectFile)
        setMessage('')
        setLoading(true)

        try {
            const result = await uploadSurveyCsv(selectFile, resultId)
            console.log("🔥 CSV 업로드 응답:", result)

            setMessage('설문 결과가 성공적으로 업로드되었습니다.')

            if (onUploaded) {
                onUploaded(result)
            }
        } catch(error){
            console.error("🔥 CSV 업로드 실패:", error)
            const detail = error.response?.data?.detail || '설문 결과 업로드에 실패했습니다.'

            setMessage(detail)
        } finally {
            setLoading(false)

            e.target.value = ''
        }
    }

    return(
        <div>
            <input ref={inputRef} type="file" accept=".csv, text/csv" onChange={handleFileChange} disabled={loading} className="hidden"/>

            <button type="button" onClick={openFilePicker} disabled={loading} className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50">
                {loading ? '업로드 중...' : 'CSV 파일 선택'}
            </button> 

            {file && (
                <p className="mt-3 text-sm text-gray-500">
                    선택된 파일: {file.name}
                </p>
            )}

            {message && (
                <p className="mt-2 text-sm text-gray-600">
                    {message}
                </p>
            )}
        </div>
    )
}