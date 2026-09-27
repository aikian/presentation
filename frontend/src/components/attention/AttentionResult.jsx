import { useState } from "react";
import { TotalScore } from "./TotalScore";
import { Graph } from "./Graph";
import { MainFactors } from "./MainFactors";

export default function AttentionResult({predictResult}){
    const [selectedFactor, setSelectedFactor] = useState(null);
    const [selectedSecond, setSelectedSecond] = useState(null);
    const [view, setView] = useState("second")

    if(!predictResult) {
        return (
            <div className="text-sm text-gray-400">
                집중도 분석 결과가 없습니다.
            </div>
        )
    }

    if (predictResult.status === "ERROR") {
        return (
            <div className="mb-8 rounded-xl border border-red-200 bg-red-50 p-6">
                <p className="text-sm font-semibold text-red-600">
                    청중 집중도를 예측하지 못했습니다.
                </p>

                <p className="mt-1 text-sm text-red-500">
                    {predictResult.message ?? "음성 분석 중 오류가 발생했습니다."}
                </p>
            </div>
        )
    }

    return(
        <div>
            <TotalScore predictResult={predictResult} />
            <Graph 
                predictResult={predictResult}
                selectedFactor={selectedFactor}
                selectedSecond={selectedSecond}
                view={view}
                onViewChange={setView} 
            />
            <MainFactors 
                predictResult={predictResult} 
                selectedFactor={selectedFactor}
                onSelectFactor={setSelectedFactor}
                selectedSecond={selectedSecond}
                onSelectSecond={setSelectedSecond}
            />
        </div>
    )
}